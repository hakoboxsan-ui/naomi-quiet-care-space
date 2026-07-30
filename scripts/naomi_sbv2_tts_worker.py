"""Generate one NAOMI WAV from stdin without logging the input text."""

from __future__ import annotations

import contextlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SBV2_ROOT = PROJECT_ROOT.parent / "AIVtuberApp" / "Style-BERT-VITS2"
DATASET_ROOT = PROJECT_ROOT.parent / "NAOMI_Voice_Datasets"
TEMP_ROOT = (Path(tempfile.gettempdir()) / "NAOMI" / "tts").resolve()
MAX_CHARACTERS = 200
_OUTPUT_NAME = re.compile(r"^naomi_v1_[0-9a-f]{32}\.wav$")


class WorkerError(Exception):
    pass


@contextlib.contextmanager
def _silence_process_output():
    """Suppress Python and native-library writes during model work."""

    sys.stdout.flush()
    sys.stderr.flush()
    saved_stdout = os.dup(1)
    saved_stderr = os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        yield
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        os.dup2(saved_stdout, 1)
        os.dup2(saved_stderr, 2)
        os.close(devnull)
        os.close(saved_stdout)
        os.close(saved_stderr)


def _fail(code: str) -> int:
    sys.stderr.write(code)
    return 1


def _output_argument(argv: list[str]) -> Path:
    if len(argv) != 2 or argv[0] != "--output":
        raise WorkerError("worker_arguments_invalid")
    output_path = Path(argv[1]).resolve()
    try:
        output_path.relative_to(TEMP_ROOT)
    except ValueError:
        raise WorkerError("worker_output_path_invalid") from None
    if output_path.parent != TEMP_ROOT or not _OUTPUT_NAME.fullmatch(output_path.name):
        raise WorkerError("worker_output_path_invalid")
    return output_path


def _load_mean_style_vector(wavs_dir: Path) -> np.ndarray:
    vector_paths = sorted(wavs_dir.glob("*.wav.npy"))
    if not vector_paths:
        raise WorkerError("worker_style_vectors_missing")
    vectors = [np.load(path, allow_pickle=False) for path in vector_paths]
    return np.expand_dims(np.mean(np.stack(vectors, axis=0), axis=0), axis=0)


def _validate_dataset_config(config_path: Path, voice_id: str, style: str) -> None:
    try:
        document = json.loads(config_path.read_text(encoding="utf-8"))
        spk2id = document["data"]["spk2id"]
        style2id = document["data"]["style2id"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        raise WorkerError("worker_dataset_config_invalid") from None
    if spk2id != {voice_id: 0} or style2id != {style: 0}:
        raise WorkerError("worker_dataset_config_mismatch")


def _generate(text: str, output_path: Path) -> None:
    sys.path.insert(0, str(PROJECT_ROOT))
    from agent.voice_spec import load_naomi_voice_spec

    spec = load_naomi_voice_spec()
    dataset_dir = (DATASET_ROOT / spec.model_candidate).resolve()
    config_path = dataset_dir / "config.json"
    wavs_dir = dataset_dir / "wavs"
    if not config_path.is_file() or not wavs_dir.is_dir():
        raise WorkerError("worker_dataset_missing")
    _validate_dataset_config(config_path, spec.voice_id, spec.style)
    style_vectors = _load_mean_style_vector(wavs_dir)

    with _silence_process_output():
        sys.path.insert(0, str(SBV2_ROOT))
        from style_bert_vits2.constants import Languages
        from style_bert_vits2.tts_model import TTSModel

        model = TTSModel(
            model_path=spec.checkpoint_path,
            config_path=config_path,
            style_vec_path=style_vectors,
            device="cuda",
        )
        sample_rate, audio = model.infer(
            text=text,
            language=Languages(spec.language),
            speaker_id=0,
            sdp_ratio=spec.sdp_ratio,
            noise=0.6,
            noise_w=0.8,
            length=spec.length,
            line_split=False,
            style=spec.style,
            style_weight=1.0,
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(output_path, audio, sample_rate, format="WAV", subtype="PCM_16")


def _decode_stdin(data: bytes) -> str:
    try:
        return data.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise WorkerError("worker_text_encoding_invalid") from None


def main(argv: list[str] | None = None) -> int:
    output_path: Path | None = None
    try:
        output_path = _output_argument(list(sys.argv[1:] if argv is None else argv))
        text = _decode_stdin(sys.stdin.buffer.read())
        if not text.strip():
            raise WorkerError("worker_text_empty")
        if len(text) > MAX_CHARACTERS:
            raise WorkerError("worker_text_too_long")
        _generate(text, output_path)
        if not output_path.is_file():
            raise WorkerError("worker_output_missing")
        sys.stdout.write(str(output_path))
        return 0
    except WorkerError as error:
        if output_path is not None:
            try:
                output_path.unlink(missing_ok=True)
            except OSError:
                pass
        return _fail(str(error))
    except Exception:
        if output_path is not None:
            try:
                output_path.unlink(missing_ok=True)
            except OSError:
                pass
        return _fail("worker_generation_failed")


if __name__ == "__main__":
    raise SystemExit(main())
