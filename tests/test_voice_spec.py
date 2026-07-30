from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Callable

from agent.voice_spec import DEFAULT_VOICE_SPEC_PATH, VoiceSpecError, load_naomi_voice_spec


class VoiceSpecTests(unittest.TestCase):
    def document(self) -> dict[str, object]:
        return json.loads(DEFAULT_VOICE_SPEC_PATH.read_text(encoding="utf-8"))

    def assert_rejected(
        self,
        mutate: Callable[[dict[str, object]], None],
        expected_code: str = "voice_spec_fixed_value_mismatch",
    ) -> None:
        document = self.document()
        mutate(document)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "project"
            path = root / "voice_specs" / "naomi_v1.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaises(VoiceSpecError) as raised:
                load_naomi_voice_spec(path, project_root=root)
        self.assertEqual(str(raised.exception), expected_code)

    def test_current_voice_spec_is_valid(self) -> None:
        before = DEFAULT_VOICE_SPEC_PATH.read_bytes()
        spec = load_naomi_voice_spec()
        self.assertEqual(spec.voice_id, "naomi_v1")
        self.assertEqual(spec.engine, "Style-BERT-VITS2")
        self.assertEqual(spec.model_candidate, "naomi_v1_good_50min_sbv2_train01")
        self.assertEqual(spec.checkpoint_step, 6000)
        self.assertEqual(spec.checkpoint_epoch, 26)
        self.assertEqual(spec.speed, 0.88)
        self.assertEqual(spec.length, 1.136364)
        self.assertEqual(spec.language, "JP")
        self.assertEqual(spec.style, "Neutral")
        self.assertEqual(spec.sdp_ratio, 0.2)
        self.assertTrue(spec.checkpoint_path.is_file())
        self.assertEqual(DEFAULT_VOICE_SPEC_PATH.read_bytes(), before)

    def test_invalid_json_returns_code_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "project"
            path = root / "voice_specs" / "naomi_v1.json"
            path.parent.mkdir(parents=True)
            path.write_text("{invalid", encoding="utf-8")
            with self.assertRaises(VoiceSpecError) as raised:
                load_naomi_voice_spec(path, project_root=root)
        self.assertEqual(str(raised.exception), "voice_spec_invalid_json")

    def test_model_candidate_mismatch_is_rejected(self) -> None:
        self.assert_rejected(
            lambda document: document["engine"].__setitem__("model_candidate", "other")
        )

    def test_checkpoint_mismatch_is_rejected(self) -> None:
        self.assert_rejected(
            lambda document: document["engine"]["checkpoint"].__setitem__(
                "filename", "other.safetensors"
            )
        )

    def test_speed_mismatch_is_rejected(self) -> None:
        self.assert_rejected(
            lambda document: document["inference"].__setitem__("speed", 0.9)
        )

    def test_language_mismatch_is_rejected(self) -> None:
        self.assert_rejected(
            lambda document: document["inference"].__setitem__("language", "EN")
        )

    def test_punctuation_policy_mismatch_is_rejected(self) -> None:
        self.assert_rejected(
            lambda document: document["inference"].__setitem__(
                "punctuation_policy", "rewrite"
            )
        )

    def test_irodori_tts_enabled_is_rejected(self) -> None:
        self.assert_rejected(
            lambda document: document["post_processing"].__setitem__(
                "irodori_tts", True
            )
        )

    def test_boolean_like_integer_is_not_accepted(self) -> None:
        self.assert_rejected(
            lambda document: document["post_processing"].__setitem__(
                "normalization", 0
            )
        )

    def test_missing_checkpoint_returns_code_only(self) -> None:
        document = self.document()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "project"
            path = root / "voice_specs" / "naomi_v1.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaises(VoiceSpecError) as raised:
                load_naomi_voice_spec(path, project_root=root)
        self.assertEqual(str(raised.exception), "checkpoint_not_found")


if __name__ == "__main__":
    unittest.main()
