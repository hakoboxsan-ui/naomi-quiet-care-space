from typing import Any, Dict, Optional

from .core import NaomiAgentCore
from .serialization import agent_response_to_payload


class NaomiAgentEngineApp:
    """Serializable Agent Engine wrapper around the existing NAOMI core."""

    def __init__(self) -> None:
        self.core = NaomiAgentCore()

    def query(self, input: str, profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        response = self.core.process_input(input, profile or {})
        payload = agent_response_to_payload(
            response,
            input_text=input,
            runtime="agent_engine",
            integration_status={"agent_engine": "called"},
        )
        payload["used_runtime"] = "agent_engine"
        return payload

    def process_free_chat(self, input: str, profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        response = self.core.process_free_chat(input, profile or {})
        payload = agent_response_to_payload(
            response,
            input_text=input,
            runtime="agent_engine",
            integration_status={"agent_engine": "called"},
        )
        payload["used_runtime"] = "agent_engine"
        return payload
