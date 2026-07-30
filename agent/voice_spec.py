"""Read-only validation for the fixed NAOMI v1 voice specification."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VOICE_SPEC_PATH = PROJECT_ROOT / "voice_specs" / "naomi_v1.json"
EXPECTED_MODEL_CANDIDATE = "naomi_v1_good_50min_sbv2_train01"
EXPECTED_CHECKPOINT_FILENAME = (
    "naomi_v1_good_50min_sbv2_train01_e26_s6000.safetensors"
)
EXPECTED_CHECKPOINT_RELATIVE_PATH = (
    "../AIVtuberApp/Style-BERT-VITS2/model_assets/"
    f"{EXPECTED_MODEL_CANDIDATE}/{EXPECTED_CHECKPOINT_FILENAME}"
)


class VoiceSpecError(Exception):
    """Public, path-free error raised while loading the voice specification."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class NaomiVoiceSpec:
    schema_version: str
    voice_id: str
    status: str
    engine: str
    model_candidate: str
    checkpoint_step: int
    checkpoint_epoch: int
    checkpoint_filename: str
    checkpoint_path: Path
    speed: float
    language: str
    style: str
    sdp_ratio: float
    length: float
    punctuation_policy: str
    style_vector_policy: str


def _mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise VoiceSpecError("voice_spec_invalid_structure")
    return value


def _require_equal(actual: Any, expected: Any) -> None:
    if type(actual) is not type(expected) or actual != expected:
        raise VoiceSpecError("voice_spec_fixed_value_mismatch")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _resolve_checkpoint(
    checkpoint: Mapping[str, Any], project_root: Path
) -> Path:
    raw_path = checkpoint.get("path")
    filename = checkpoint.get("filename")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise VoiceSpecError("checkpoint_path_invalid")
    if not isinstance(filename, str) or not filename.strip():
        raise VoiceSpecError("checkpoint_path_invalid")

    relative_path = Path(raw_path)
    if relative_path.is_absolute() or relative_path.name != filename:
        raise VoiceSpecError("checkpoint_path_invalid")
    if raw_path.replace("\\", "/") != EXPECTED_CHECKPOINT_RELATIVE_PATH:
        raise VoiceSpecError("checkpoint_path_invalid")
    if relative_path.suffix.lower() != ".safetensors":
        raise VoiceSpecError("checkpoint_path_invalid")

    resolved_root = project_root.resolve()
    approved_root = (
        resolved_root.parent
        / "AIVtuberApp"
        / "Style-BERT-VITS2"
        / "model_assets"
    ).resolve()
    resolved_path = (resolved_root / relative_path).resolve()
    if not _is_relative_to(resolved_path, approved_root):
        raise VoiceSpecError("checkpoint_path_invalid")
    if not resolved_path.exists():
        raise VoiceSpecError("checkpoint_not_found")
    if not resolved_path.is_file():
        raise VoiceSpecError("checkpoint_not_file")
    return resolved_path


def load_naomi_voice_spec(
    spec_path: Path | str = DEFAULT_VOICE_SPEC_PATH,
    *,
    project_root: Path | str | None = None,
) -> NaomiVoiceSpec:
    """Load and validate ``naomi_v1.json`` without modifying it."""

    path = Path(spec_path)
    root = Path(project_root) if project_root is not None else path.parent.parent
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise VoiceSpecError("voice_spec_not_found") from None
    except OSError:
        raise VoiceSpecError("voice_spec_read_failed") from None

    try:
        document = _mapping(json.loads(raw))
    except json.JSONDecodeError:
        raise VoiceSpecError("voice_spec_invalid_json") from None

    engine = _mapping(document.get("engine"))
    checkpoint = _mapping(engine.get("checkpoint"))
    inference = _mapping(document.get("inference"))
    post_processing = _mapping(document.get("post_processing"))

    _require_equal(document.get("schema_version"), "1.0")
    _require_equal(document.get("voice_id"), "naomi_v1")
    _require_equal(document.get("status"), "fixed_candidate")
    _require_equal(engine.get("name"), "Style-BERT-VITS2")
    _require_equal(engine.get("model_candidate"), EXPECTED_MODEL_CANDIDATE)
    _require_equal(checkpoint.get("step"), 6000)
    _require_equal(checkpoint.get("epoch"), 26)
    _require_equal(checkpoint.get("filename"), EXPECTED_CHECKPOINT_FILENAME)
    _require_equal(inference.get("speed"), 0.88)
    _require_equal(inference.get("length"), 1.136364)
    _require_equal(inference.get("language"), "JP")
    _require_equal(inference.get("style"), "Neutral")
    _require_equal(inference.get("sdp_ratio"), 0.2)
    _require_equal(
        inference.get("punctuation_policy"),
        "preserve_original_natural_punctuation",
    )
    _require_equal(
        inference.get("style_vector_policy"),
        "use_trained_audio_mean_style_vector",
    )
    _require_equal(post_processing.get("irodori_tts"), False)
    _require_equal(post_processing.get("normalization"), False)
    _require_equal(post_processing.get("limiter"), False)
    _require_equal(post_processing.get("automatic_volume_processing"), False)

    checkpoint_path = _resolve_checkpoint(checkpoint, root)
    return NaomiVoiceSpec(
        schema_version="1.0",
        voice_id="naomi_v1",
        status="fixed_candidate",
        engine="Style-BERT-VITS2",
        model_candidate=EXPECTED_MODEL_CANDIDATE,
        checkpoint_step=6000,
        checkpoint_epoch=26,
        checkpoint_filename=EXPECTED_CHECKPOINT_FILENAME,
        checkpoint_path=checkpoint_path,
        speed=0.88,
        language="JP",
        style="Neutral",
        sdp_ratio=0.2,
        length=1.136364,
        punctuation_policy="preserve_original_natural_punctuation",
        style_vector_policy="use_trained_audio_mean_style_vector",
    )
