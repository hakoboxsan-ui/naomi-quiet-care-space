from __future__ import annotations

import ast
import unittest
from pathlib import Path


SOURCE_PATH = Path(__file__).resolve().parents[1] / "frontend" / "streamlit_app.py"


class VoiceUIStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SOURCE_PATH.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)
        cls.parents: dict[ast.AST, ast.AST] = {}
        for parent in ast.walk(cls.tree):
            for child in ast.iter_child_nodes(parent):
                cls.parents[child] = parent
        cls.render_function = next(
            node
            for node in cls.tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "render_voice_controls"
        )

    @staticmethod
    def _call_name(call: ast.Call) -> str:
        if isinstance(call.func, ast.Name):
            return call.func.id
        if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name):
            return f"{call.func.value.id}.{call.func.attr}"
        return ""

    def test_adapter_creation_occurs_only_inside_button_branch(self) -> None:
        calls = [
            node
            for node in ast.walk(self.render_function)
            if isinstance(node, ast.Call)
            and self._call_name(node) == "create_default_controller"
        ]
        self.assertEqual(len(calls), 1)
        ancestor = self.parents[calls[0]]
        while ancestor is not self.render_function and not isinstance(ancestor, ast.If):
            ancestor = self.parents[ancestor]
        self.assertIsInstance(ancestor, ast.If)
        button_calls = [
            node
            for node in ast.walk(ancestor.test)
            if isinstance(node, ast.Call) and self._call_name(node) == "st.button"
        ]
        self.assertEqual(len(button_calls), 1)

    def test_audio_player_explicitly_disables_autoplay(self) -> None:
        audio_calls = [
            node
            for node in ast.walk(self.render_function)
            if isinstance(node, ast.Call) and self._call_name(node) == "st.audio"
        ]
        self.assertEqual(len(audio_calls), 1)
        autoplay = next(
            keyword.value for keyword in audio_calls[0].keywords if keyword.arg == "autoplay"
        )
        self.assertIsInstance(autoplay, ast.Constant)
        self.assertIs(autoplay.value, False)

    def test_required_safe_messages_are_present(self) -> None:
        self.assertIn(
            "周囲に音声が聞こえる可能性があります。必要なときだけご利用ください。",
            self.source,
        )
        self.assertIn(
            "この文章は長いため、現在の音声機能では読み上げられません。文章はそのままお読みいただけます。",
            self.source,
        )
        self.assertIn(
            "音声を準備できませんでした。文章はそのままご利用いただけます。",
            self.source,
        )

    def test_no_audio_and_answer_change_discard_session_audio(self) -> None:
        sync_function = next(
            node
            for node in self.tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "sync_voice_state"
        )
        sync_source = ast.get_source_segment(self.source, sync_function) or ""
        self.assertIn("acc_no_audio", sync_source)
        self.assertIn("naomi_voice_result_digest", sync_source)
        self.assertGreaterEqual(sync_source.count("discard_voice_audio"), 2)

    def test_voice_controls_are_attached_after_each_response_surface(self) -> None:
        calls = [
            node
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Call)
            and self._call_name(node) == "render_voice_controls"
        ]
        keys = {
            keyword.value.value
            for call in calls
            for keyword in call.keywords
            if keyword.arg == "key" and isinstance(keyword.value, ast.Constant)
        }
        self.assertEqual(keys, {"start", "home", "state", "bottom"})

    def test_hackathon_runtime_integrations_are_hidden(self) -> None:
        debug_function = next(
            node
            for node in self.tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "show_hackathon_runtime_debug"
        )
        self.assertEqual(len(debug_function.body), 1)
        self.assertIsInstance(debug_function.body[0], ast.Return)


if __name__ == "__main__":
    unittest.main()
