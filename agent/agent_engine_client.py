import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def is_agent_engine_enabled() -> bool:
    return bool(os.getenv("NAOMI_AGENT_ENGINE_RESOURCE"))


def query_agent_engine(text: str, profile: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    resource = os.getenv("NAOMI_AGENT_ENGINE_RESOURCE")
    if not resource:
        return None

    try:
        import vertexai

        project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION") or os.getenv("GOOGLE_CLOUD_REGION") or "us-central1"
        vertexai.init(project=project, location=location)

        remote_agent = _get_remote_agent(resource)
        if remote_agent is None:
            raise RuntimeError("No compatible Agent Engine client found in installed google-cloud-aiplatform.")

        return _call_remote_agent(remote_agent, text, profile or {})
    except Exception:
        logger.exception("Agent Engine runtime call failed")
        raise


def _get_remote_agent(resource: str) -> Any:
    try:
        from vertexai import agent_engines

        if hasattr(agent_engines, "get"):
            return agent_engines.get(resource)
    except Exception as exc:
        logger.info("vertexai.agent_engines unavailable: %s", exc)

    try:
        from vertexai.preview import reasoning_engines

        if hasattr(reasoning_engines, "ReasoningEngine"):
            return reasoning_engines.ReasoningEngine(resource)
        if hasattr(reasoning_engines, "get"):
            return reasoning_engines.get(resource)
    except Exception as exc:
        logger.info("vertexai.preview.reasoning_engines unavailable: %s", exc)

    return None


def _call_remote_agent(remote_agent: Any, text: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    attempts = [
        ("query_kwargs", lambda: remote_agent.query(input=text, profile=profile)),
        ("query_dict", lambda: remote_agent.query({"input": text, "profile": profile})),
        ("query_text", lambda: remote_agent.query(text)),
        ("stream_query_kwargs", lambda: list(remote_agent.stream_query(input=text, profile=profile))[-1]),
    ]
    last_error: Optional[Exception] = None
    for name, call in attempts:
        if name.startswith("stream") and not hasattr(remote_agent, "stream_query"):
            continue
        if name.startswith("query") and not hasattr(remote_agent, "query"):
            continue
        try:
            result = call()
            if isinstance(result, dict):
                result["agent_engine_call_style"] = name
                return result
            return {"text": str(result), "agent_engine_call_style": name}
        except Exception as exc:
            last_error = exc
            logger.info("Agent Engine call style %s failed: %s", name, exc)
    raise RuntimeError(f"No compatible Agent Engine query signature succeeded: {last_error}")
