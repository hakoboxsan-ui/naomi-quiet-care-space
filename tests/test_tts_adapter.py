from __future__ import annotations

import io
import logging
import subprocess
import tempfile
import threading
import unittest
import wave
from pathlib import Path

from agent.tts_adapter import (
    FAILED,
    READY,
    RUNNING,
    TIMED_OUT,
    SubprocessWorkerRunner,
    TTSAdapterConfig,
    TTSAdapterError,
    TTSController,
    WorkerRequest,
    WorkerResult,
)
from scripts.naomi_sbv2_tts_worker import WorkerError, _decode_stdin


SENSITIVE_TEXT = "個人情報を含むテスト本文です"


def valid_wav_bytes() -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(44100)
        wav_file.writeframes(b"\x00\x00" * 100)
    return buffer.getvalue()


class RecordingRunner:
    def __init__(
        self,
        *,
        return_code: int = 0,
        wav_data: bytes | None = None,
        stderr: bytes = b"",
        error: Exception | None = None,
    ) -> None:
        self.return_code = return_code
        self.wav_data = wav_data
        self.stderr = stderr
        self.error = error
        self.requests: list[WorkerRequest] = []
        self.timeouts: list[float] = []
        self.cancelled = False

    def __call__(self, request: WorkerRequest, timeout_seconds: float) -> WorkerResult:
        self.requests.append(request)
        self.timeouts.append(timeout_seconds)
        if self.error is not None:
            raise self.error
        if self.wav_data is not None:
            request.output_path.write_bytes(self.wav_data)
        return WorkerResult(
            self.return_code,
            str(request.output_path).encode("utf-8"),
            self.stderr,
        )

    def cancel(self) -> None:
        self.cancelled = True


class BlockingRunner(RecordingRunner):
    def __init__(self) -> None:
        super().__init__(wav_data=valid_wav_bytes())
        self.started = threading.Event()
        self.release = threading.Event()

    def __call__(self, request: WorkerRequest, timeout_seconds: float) -> WorkerResult:
        self.started.set()
        self.release.wait(timeout=2.0)
        return super().__call__(request, timeout_seconds)


class FakePopen:
    def __init__(self, argv: tuple[str, ...], **kwargs: object) -> None:
        self.argv = argv
        self.kwargs = kwargs
        self.pid = 1234
        self.returncode = 0
        self.stdin_payload: bytes | None = None
        self.timeout: float | None = None

    def communicate(
        self, input: bytes | None = None, timeout: float | None = None
    ) -> tuple[bytes, bytes]:
        self.stdin_payload = input
        self.timeout = timeout
        return b"worker-output", b""

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.returncode = -15

    def wait(self, timeout: float | None = None) -> int:
        return self.returncode

    def kill(self) -> None:
        self.returncode = -9


class TimeoutPopen(FakePopen):
    def communicate(
        self, input: bytes | None = None, timeout: float | None = None
    ) -> tuple[bytes, bytes]:
        if self.returncode == 0:
            raise subprocess.TimeoutExpired(self.argv, timeout)
        return b"", b""


class TTSAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.temp_dir = Path(self.temp.name) / "NAOMI" / "tts"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def config(self, **overrides: object) -> TTSAdapterConfig:
        values = {
            "enabled": True,
            "is_windows_local": True,
            "temp_dir": self.temp_dir,
            "worker_command": ("python.exe", "scripts/naomi_sbv2_tts_worker.py"),
        }
        values.update(overrides)
        return TTSAdapterConfig(**values)

    def test_feature_flag_defaults_off(self) -> None:
        config = TTSAdapterConfig.from_environment(
            {}, system_name="Windows", temp_dir=self.temp_dir
        )
        self.assertFalse(config.enabled)

    def test_feature_flag_false_is_off(self) -> None:
        config = TTSAdapterConfig.from_environment(
            {"NAOMI_VOICE_ENABLED": "false"},
            system_name="Windows",
            temp_dir=self.temp_dir,
        )
        self.assertFalse(config.enabled)

    def test_feature_flag_true_is_on(self) -> None:
        config = TTSAdapterConfig.from_environment(
            {"NAOMI_VOICE_ENABLED": "true"},
            system_name="Windows",
            temp_dir=self.temp_dir,
        )
        self.assertTrue(config.enabled)

    def test_legacy_flag_is_not_accepted(self) -> None:
        config = TTSAdapterConfig.from_environment(
            {"NAOMI_TTS_ENABLED": "true"},
            system_name="Windows",
            temp_dir=self.temp_dir,
        )
        self.assertFalse(config.enabled)

    def test_disabled_controller_never_runs_worker(self) -> None:
        runner = RecordingRunner(wav_data=valid_wav_bytes())
        controller = TTSController(self.config(enabled=False), runner)
        with self.assertRaises(TTSAdapterError) as raised:
            controller.synthesize_wav("短い本文")
        self.assertEqual(str(raised.exception), "tts_feature_disabled")
        self.assertEqual(runner.requests, [])

    def test_no_audio_rejects_without_running_worker(self) -> None:
        runner = RecordingRunner(wav_data=valid_wav_bytes())
        controller = TTSController(self.config(), runner)
        with self.assertRaises(TTSAdapterError) as raised:
            controller.synthesize_wav("短い本文", acc_no_audio=True)
        self.assertEqual(str(raised.exception), "tts_audio_disabled")
        self.assertEqual(runner.requests, [])

    def test_subprocess_uses_stdin_and_no_shell(self) -> None:
        created: list[FakePopen] = []

        def factory(argv: tuple[str, ...], **kwargs: object) -> FakePopen:
            process = FakePopen(argv, **kwargs)
            created.append(process)
            return process

        runner = SubprocessWorkerRunner(popen_factory=factory)
        request = WorkerRequest(
            text=SENSITIVE_TEXT,
            output_path=self.temp_dir / "naomi_v1_00000000000000000000000000000000.wav",
            argv=("python.exe", "worker.py", "--output", "safe.wav"),
            environment={},
        )
        runner(request, 12.0)
        process = created[0]
        self.assertEqual(process.stdin_payload, SENSITIVE_TEXT.encode("utf-8"))
        self.assertIs(process.kwargs["shell"], False)
        self.assertEqual(process.kwargs["stdin"], subprocess.PIPE)
        self.assertNotIn(SENSITIVE_TEXT, " ".join(process.argv))

    def test_worker_decodes_japanese_stdin_as_utf8(self) -> None:
        text = "今日は、どのようなことで来られましたか。"
        self.assertEqual(_decode_stdin(text.encode("utf-8")), text)

    def test_worker_rejects_invalid_utf8_without_echoing_input(self) -> None:
        with self.assertRaisesRegex(WorkerError, "^worker_text_encoding_invalid$"):
            _decode_stdin(b"\x81")

    def test_subprocess_timeout_terminates_process(self) -> None:
        terminated: list[FakePopen] = []

        def factory(argv: tuple[str, ...], **kwargs: object) -> TimeoutPopen:
            return TimeoutPopen(argv, **kwargs)

        def terminate(process: FakePopen) -> None:
            terminated.append(process)
            process.returncode = -9

        runner = SubprocessWorkerRunner(
            popen_factory=factory,
            process_terminator=terminate,
        )
        controller = TTSController(self.config(timeout_seconds=0.01), runner)
        with self.assertRaises(TTSAdapterError) as raised:
            controller.synthesize_wav("timeout")
        self.assertEqual(str(raised.exception), "tts_worker_timeout")
        self.assertEqual(controller.snapshot.state, TIMED_OUT)
        self.assertEqual(len(terminated), 1)
        self.assertEqual(list(self.temp_dir.glob("*.wav")), [])

    def test_success_returns_bytes_and_removes_temp_wav(self) -> None:
        expected = valid_wav_bytes()
        runner = RecordingRunner(wav_data=expected)
        controller = TTSController(self.config(), runner)
        actual = controller.synthesize_wav("成功テスト")
        self.assertEqual(actual, expected)
        self.assertEqual(controller.snapshot.state, READY)
        self.assertFalse(runner.requests[0].output_path.exists())

    def test_worker_failure_removes_partial_temp_wav(self) -> None:
        runner = RecordingRunner(return_code=3, wav_data=b"partial")
        controller = TTSController(self.config(), runner)
        with self.assertRaises(TTSAdapterError) as raised:
            controller.synthesize_wav("失敗テスト")
        self.assertEqual(str(raised.exception), "tts_worker_failed")
        self.assertEqual(controller.snapshot.state, FAILED)
        self.assertFalse(runner.requests[0].output_path.exists())

    def test_invalid_wav_is_rejected_and_removed(self) -> None:
        runner = RecordingRunner(wav_data=b"not a wav" * 20)
        controller = TTSController(self.config(), runner)
        with self.assertRaises(TTSAdapterError) as raised:
            controller.synthesize_wav("不正WAV")
        self.assertEqual(str(raised.exception), "tts_wav_invalid")
        self.assertFalse(runner.requests[0].output_path.exists())

    def test_long_text_is_not_truncated_or_sent(self) -> None:
        runner = RecordingRunner(wav_data=valid_wav_bytes())
        controller = TTSController(self.config(), runner)
        text = "あ" * 201
        with self.assertRaises(TTSAdapterError) as raised:
            controller.synthesize_wav(text)
        self.assertEqual(str(raised.exception), "tts_text_too_long")
        self.assertEqual(runner.requests, [])

    def test_concurrent_generation_is_rejected(self) -> None:
        runner = BlockingRunner()
        controller = TTSController(self.config(), runner)
        errors: list[Exception] = []

        def first_call() -> None:
            try:
                controller.synthesize_wav("一件目")
            except Exception as error:
                errors.append(error)

        thread = threading.Thread(target=first_call)
        thread.start()
        self.assertTrue(runner.started.wait(timeout=1.0))
        self.assertEqual(controller.snapshot.state, RUNNING)
        with self.assertRaises(TTSAdapterError) as raised:
            controller.synthesize_wav("二件目")
        self.assertEqual(str(raised.exception), "tts_job_already_running")
        runner.release.set()
        thread.join(timeout=2.0)
        self.assertEqual(errors, [])

    def test_sensitive_text_is_absent_from_external_surfaces_and_logs(self) -> None:
        runner = RecordingRunner(return_code=7)
        controller = TTSController(self.config(), runner)
        records: list[logging.LogRecord] = []

        class CaptureHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record)

        handler = CaptureHandler()
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        try:
            with self.assertRaises(TTSAdapterError) as raised:
                controller.synthesize_wav(SENSITIVE_TEXT)
        finally:
            root_logger.removeHandler(handler)
        request = runner.requests[0]
        surfaces = [
            " ".join(request.argv),
            " ".join(f"{key}={value}" for key, value in request.environment.items()),
            request.output_path.name,
            repr(request),
            repr(WorkerResult(1, SENSITIVE_TEXT.encode(), SENSITIVE_TEXT.encode())),
            str(raised.exception),
            "\n".join(record.getMessage() for record in records),
        ]
        self.assertEqual(request.text, SENSITIVE_TEXT)
        self.assertTrue(all(SENSITIVE_TEXT not in surface for surface in surfaces))


if __name__ == "__main__":
    unittest.main()
