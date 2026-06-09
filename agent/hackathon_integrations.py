import logging
import os
import uuid
from typing import Any, Dict, Optional

from .agent_engine_client import is_agent_engine_enabled, query_agent_engine
from .arize_mcp_client import call_arize_mcp
from .arize_tracing import trace_naomi_turn
from .core import AgentResponse, NaomiAgentCore
from .serialization import agent_response_to_payload, dict_to_agent_response

logger = logging.getLogger(__name__)


def integrations_enabled() -> bool:
    return os.getenv("ENABLE_HACKATHON_INTEGRATIONS", "").lower() == "true"


def process_with_hackathon_integrations(
    text: str,
    profile: Optional[Dict[str, Any]],
    local_core: NaomiAgentCore,
    *,
    free_chat: bool = False,
) -> AgentResponse:
    trace_id = str(uuid.uuid4())
    status: Dict[str, Any] = {
        "enabled": integrations_enabled(),
        "trace_id": trace_id,
        "gemini": "called" if getattr(getattr(local_core, "gemini", None), "is_available", False) else "fallback",
        "agent_engine": "disabled",
        "arize_mcp": "disabled",
        "phoenix_otel": "disabled",
    }

    runtime = "local"
    response: AgentResponse

    if integrations_enabled() and is_agent_engine_enabled():
        try:
            remote_payload = query_agent_engine(text, profile or {})
            if remote_payload:
                response = dict_to_agent_response(remote_payload)
                runtime = "agent_engine"
                status["agent_engine"] = "called"
            else:
                response = _local_process(local_core, text, profile, free_chat)
                status["agent_engine"] = "fallback"
        except Exception:
            logger.exception("Agent Engine runtime call failed")
            response = _local_process(local_core, text, profile, free_chat)
            status["agent_engine"] = "failed"
    else:
        response = _local_process(local_core, text, profile, free_chat)
        status["agent_engine"] = "disabled" if not is_agent_engine_enabled() else "fallback"

    payload = agent_response_to_payload(
        response,
        input_text=text,
        trace_id=trace_id,
        runtime=runtime,
        integration_status=status,
    )
    payload["used_gemini"] = status["gemini"] == "called"

    if integrations_enabled():
        arize_result = call_arize_mcp(payload)
        status["arize_mcp"] = arize_result.get("status", "failed")
        payload["arize_mcp_result"] = arize_result
    else:
        payload["arize_mcp_result"] = {"status": "disabled", "reason": "ENABLE_HACKATHON_INTEGRATIONS is not true"}

    payload["integration_status"] = status
    trace_result = trace_naomi_turn(payload)
    status["phoenix_otel"] = trace_result.get("status", "disabled")
    payload["phoenix_otel_result"] = trace_result
    setattr(response, "_hackathon_debug", payload)
    return response


def _local_process(
    local_core: NaomiAgentCore,
    text: str,
    profile: Optional[Dict[str, Any]],
    free_chat: bool,
) -> AgentResponse:
    if free_chat and hasattr(local_core, "process_free_chat"):
        return local_core.process_free_chat(text, profile)
    return local_core.process_input(text, profile)
