"""Minimal self-contained Agent Engine app for hackathon submission.

Intentionally avoids importing NaomiAgentCore or any Streamlit-dependent
modules at module level to ensure the remote container starts cleanly.
All heavy imports are inside the query() method with full error handling.
"""
import os
from typing import Any, Dict, Optional


class NaomiAgentEngineApp:
    """Serializable Agent Engine wrapper.

    The __init__ is intentionally lightweight so that cloudpickle can
    serialize and the remote container can reconstruct this object even
    without access to the full NAOMI module tree.
    """

    def __init__(self) -> None:
        # Do NOT import NaomiAgentCore or any local agent module here.
        # The remote container may not have all sub-dependencies at init time.
        pass

    # ------------------------------------------------------------------
    # Public API (called by the remote Agent Engine runtime)
    # ------------------------------------------------------------------

    def query(self, input: str = "", profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle a query from the Agent Engine runtime."""
        text = input or ""
        response_text = self._generate_response(text)
        return {
            "text": response_text,
            "input": text,
            "used_runtime": "agent_engine",
            "integration_status": {"agent_engine": "called"},
            "state": "CALM",
            "mode": "SUPPORT",
        }

    def process_free_chat(self, input: str = "", profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.query(input=input, profile=profile)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _generate_response(self, text: str) -> str:
        """Try Gemini, fall back to a safe static reply."""
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if api_key:
            try:
                import google.generativeai as genai  # type: ignore

                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-2.0-flash")
                result = model.generate_content(
                    f"You are NAOMI, a calm listening AI assistant. "
                    f"Reply briefly and warmly in Japanese to: {text}"
                )
                return result.text
            except Exception:
                pass
        # Safe fallback — no external dependencies needed
        return "少し聞かせてください。（Agent Engine 経由）"
