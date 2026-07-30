"""Safe subprocess boundary for user-triggered NAOMI voice generation."""

from __future__ import annotations

import io
import os
import platform
import re
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import wave
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Mapping, Protocol, Sequence


IDLE = "idle"
RUNNING = "running"
READY = "ready"
FAILED = "failed"
TIMED_OUT = "timed_out"
CANCELLED = "cancelled"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKER_PATH = PROJECT_ROOT / "scripts" / "naomi_sbv2_tts_worker.py"
DEFAULT_SBV2_PYTHON = (
    PROJECT_ROOT.parent
    / "AIVtuberApp"
    / "Style-BERT-VITS2"
    / "venv"
    / "Scripts"
    / "python.exe"
)
MAX_CHARACTERS = 200
MIN_WAV_BYTES = 128
_OUTPUT_NAME = re.compile(r"^naomi_v1_[0-9a-f]{32}\.wav$")


class TTSAdapterError(Exception):
    """Public, text-free controller error."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class WorkerTimedOut(Exception):
    """Internal timeout marker that never includes input text."""


@dataclass(frozen=True)
class WorkerRequest:
    """The text remains in memory and is sent only through subprocess stdin."""

    text: str = field(repr=False)
    output_path: Path
    argv: tuple[str, ...]
    environment: Mapping[str, str]


@dataclass(frozen=True)
class WorkerResult:
    return_code: int
    stdout: bytes = field(repr=False)
    stderr: bytes = field(repr=False)


class WorkerRunner(Protocol):
    def __call__(self, request: WorkerRequest, timeout_seconds: float) -> WorkerResult: ...


class ProcessHandle(Protocol):
    pid: int

    def poll(self) -> int | None: ...

    def terminate(self) -> None: ...

    def wait(self, timeout: float | None = None) -> int: ...

    def kill(self) -> None: ...


def _enabled(value: str | None) -> bool:
    return (value or "").strip().lower() == "true"


def _default_worker_command() -> tuple[str, ...]:
    return (str(DEFAULT_SBV2_PYTHON), str(DEFAULT_WORKER_PATH))


@dataclass(frozen=True)
class TTSAdapterConfig:
    enabled: bool = False
    is_windows_local: bool = False
    timeout_seconds: float = 300.0
    max_characters: int = MAX_CHARACTERS
    temp_dir: Path = field(
        default_factory=lambda: Path(tempfile.gettempdir()) / "NAOMI" / "tts"
    )
    worker_command: tuple[str, ...] = field(default_factory=_default_worker_command)
    worker_environment: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType({})
    )

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
        *,
        system_name: str | None = None,
        temp_dir: Path | str | None = None,
    ) -> "TTSAdapterConfig":
        env = os.environ if environment is None else environment
        system = platform.system() if system_name is None else system_name
        return cls(
            enabled=_enabled(env.get("NAOMI_VOICE_ENABLED")),
            is_windows_local=system == "Windows",
            temp_dir=(
                Path(temp_dir)
                if temp_dir is not None
                else Path(tempfile.gettempdir()) / "NAOMI" / "tts"
            ),
        )


def terminate_process_tree(process: ProcessHandle) -> None:
    """Best-effort termination, including the Windows child process tree."""

    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                check=False,
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5.0,
            )
        except (OSError, subprocess.SubprocessError):
            pass
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=2.0)
    except Exception:
        try:
            process.kill()
            process.wait(timeout=2.0)
        except Exception:
            return


class SubprocessWorkerRunner:
    """Launch only the configured worker without a shell and write text to stdin."""

    def __init__(
        self,
        *,
        popen_factory: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
        process_terminator: Callable[[ProcessHandle], None] = terminate_process_tree,
    ) -> None:
        self._popen_factory = popen_factory
        self._process_terminator = process_terminator
        self._active_process: ProcessHandle | None = None
        self._lock = threading.Lock()

    def __call__(self, request: WorkerRequest, timeout_seconds: float) -> WorkerResult:
        creationflags = 0
        if os.name == "nt":
            creationflags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
            creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        process = self._popen_factory(
            request.argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(PROJECT_ROOT),
            env=dict(request.environment) if request.environment else None,
            shell=False,
            creationflags=creationflags,
        )
        with self._lock:
            self._active_process = process
        try:
            try:
                stdout, stderr = process.communicate(
                    input=request.text.encode("utf-8"),
                    timeout=timeout_seconds,
                )
            except subprocess.TimeoutExpired:
                self._process_terminator(process)
                try:
                    process.communicate(timeout=2.0)
                except Exception:
                    pass
                raise WorkerTimedOut("tts_worker_timeout") from None
            return WorkerResult(process.returncode or 0, stdout or b"", stderr or b"")
        finally:
            with self._lock:
                if self._active_process is process:
                    self._active_process = None

    def cancel(self) -> None:
        with self._lock:
            process = self._active_process
        if process is not None:
            self._process_terminator(process)


@dataclass(frozen=True)
class JobSnapshot:
    state: str
    error_code: str | None = None


class TTSController:
    def __init__(
        self,
        config: TTSAdapterConfig,
        worker_runner: WorkerRunner,
        *,
        wall_clock: Callable[[], float] = time.time,
    ) -> None:
        self._config = config
        self._worker_runner = worker_runner
        self._wall_clock = wall_clock
        self._state = IDLE
        self._error_code: str | None = None
        self._output_path: Path | None = None
        self._state_lock = threading.Lock()

    @property
    def snapshot(self) -> JobSnapshot:
        with self._state_lock:
            return JobSnapshot(self._state, self._error_code)

    def _raise(self, code: str) -> None:
        raise TTSAdapterError(code)

    def _require_available(self, acc_no_audio: bool) -> None:
        if not self._config.enabled:
            self._raise("tts_feature_disabled")
        if not self._config.is_windows_local:
            self._raise("tts_platform_unsupported")
        if acc_no_audio:
            self._raise("tts_audio_disabled")

    def _validate_text(self, text: str) -> str:
        if not isinstance(text, str) or not text.strip():
            self._raise("tts_text_empty")
        if len(text) > self._config.max_characters:
            self._raise("tts_text_too_long")
        return text

    def _resolved_temp_dir(self) -> Path:
        return self._config.temp_dir.resolve()

    def validate_output_path(self, path: Path | str) -> Path:
        candidate = Path(path).resolve()
        root = self._resolved_temp_dir()
        try:
            candidate.relative_to(root)
        except ValueError:
            raise TTSAdapterError("tts_output_path_invalid") from None
        if candidate.parent != root or not _OUTPUT_NAME.fullmatch(candidate.name):
            self._raise("tts_output_path_invalid")
        return candidate

    def create_output_path(self) -> Path:
        root = self._resolved_temp_dir()
        root.mkdir(parents=True, exist_ok=True)
        return self.validate_output_path(root / f"naomi_v1_{uuid.uuid4().hex}.wav")

    @staticmethod
    def _validate_wav_bytes(data: bytes) -> None:
        if len(data) < MIN_WAV_BYTES:
            raise TTSAdapterError("tts_wav_invalid")
        try:
            with wave.open(io.BytesIO(data), "rb") as wav_file:
                valid = (
                    wav_file.getnchannels() > 0
                    and wav_file.getsampwidth() > 0
                    and wav_file.getframerate() > 0
                    and wav_file.getnframes() > 0
                    and wav_file.getcomptype() == "NONE"
                )
        except (EOFError, wave.Error):
            raise TTSAdapterError("tts_wav_invalid") from None
        if not valid:
            raise TTSAdapterError("tts_wav_invalid")

    def _set_terminal(self, state: str, error_code: str | None) -> None:
        with self._state_lock:
            self._state = state
            self._error_code = error_code

    def synthesize_wav(self, text: str, *, acc_no_audio: bool = False) -> bytes:
        """Generate WAV bytes synchronously and immediately remove the temp file."""

        self._require_available(acc_no_audio)
        validated_text = self._validate_text(text)
        with self._state_lock:
            if self._state == RUNNING:
                self._raise("tts_job_already_running")
            self._state = RUNNING
            self._error_code = None

        output_path = self.create_output_path()
        self._output_path = output_path
        request = WorkerRequest(
            text=validated_text,
            output_path=output_path,
            argv=(*self._config.worker_command, "--output", str(output_path)),
            environment=MappingProxyType(dict(self._config.worker_environment)),
        )
        try:
            try:
                result = self._worker_runner(request, self._config.timeout_seconds)
            except WorkerTimedOut:
                self._set_terminal(TIMED_OUT, "tts_worker_timeout")
                raise TTSAdapterError("tts_worker_timeout") from None
            except Exception:
                self._set_terminal(FAILED, "tts_worker_start_failed")
                raise TTSAdapterError("tts_worker_start_failed") from None

            if result.return_code != 0:
                self._set_terminal(FAILED, "tts_worker_failed")
                raise TTSAdapterError("tts_worker_failed")
            try:
                reported_path = Path(result.stdout.decode("utf-8").strip()).resolve()
            except (UnicodeDecodeError, OSError, ValueError):
                self._set_terminal(FAILED, "tts_worker_protocol_invalid")
                raise TTSAdapterError("tts_worker_protocol_invalid") from None
            if reported_path != output_path or result.stderr.strip():
                self._set_terminal(FAILED, "tts_worker_protocol_invalid")
                raise TTSAdapterError("tts_worker_protocol_invalid")
            if not output_path.is_file():
                self._set_terminal(FAILED, "tts_worker_output_missing")
                raise TTSAdapterError("tts_worker_output_missing")

            try:
                wav_bytes = output_path.read_bytes()
            except OSError:
                self._set_terminal(FAILED, "tts_worker_output_read_failed")
                raise TTSAdapterError("tts_worker_output_read_failed") from None
            try:
                self._validate_wav_bytes(wav_bytes)
            except TTSAdapterError:
                self._set_terminal(FAILED, "tts_wav_invalid")
                raise

            self._set_terminal(READY, None)
            return wav_bytes
        finally:
            self._safe_unlink(output_path)
            self._output_path = None

    def stop(self) -> JobSnapshot:
        if self.snapshot.state == RUNNING:
            cancel = getattr(self._worker_runner, "cancel", None)
            if callable(cancel):
                cancel()
            self._safe_unlink(self._output_path)
            self._set_terminal(CANCELLED, "tts_job_cancelled")
        return self.snapshot

    def set_no_audio(self, enabled: bool) -> JobSnapshot:
        if enabled:
            self.stop()
        return self.snapshot

    def cleanup_stale_files(self, *, now: float | None = None) -> tuple[str, ...]:
        """Crash-recovery fallback; current jobs are deleted immediately."""

        root = self._resolved_temp_dir()
        if not root.exists() or not root.is_dir():
            return ()
        cutoff = (self._wall_clock() if now is None else now) - 24 * 60 * 60
        removed: list[str] = []
        for candidate in root.iterdir():
            if candidate.is_symlink() or not candidate.is_file():
                continue
            if not _OUTPUT_NAME.fullmatch(candidate.name):
                continue
            try:
                if candidate.stat().st_mtime >= cutoff:
                    continue
                candidate.unlink()
                removed.append(candidate.name)
            except OSError:
                continue
        return tuple(sorted(removed))

    @staticmethod
    def _safe_unlink(path: Path | None) -> None:
        if path is None:
            return
        try:
            if path.is_file() or path.is_symlink():
                path.unlink()
        except OSError:
            return


def create_default_controller() -> TTSController:
    return TTSController(
        TTSAdapterConfig.from_environment(),
        SubprocessWorkerRunner(),
    )
