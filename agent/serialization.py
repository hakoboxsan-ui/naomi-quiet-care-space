from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, Dict, Optional

from .behavior_policy import AgentStrategy
from .core import AgentResponse
from .mode_selector import Mode
from .state_engine import HumanState


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, Enum):
        return value.name
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item) for item in value]
    return value


def agent_response_to_dict(response: AgentResponse) -> Dict[str, Any]:
    data = to_jsonable(response)
    data["mode"] = _enum_name(getattr(response, "mode", None))
    return data


def agent_response_to_payload(
    response: AgentResponse,
    *,
    input_text: str = "",
    trace_id: str = "",
    runtime: str = "local",
    integration_status: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    data = agent_response_to_dict(response)
    data.update(
        {
            "input_length": len(input_text or ""),
            "trace_id": trace_id,
            "used_runtime": runtime,
            "integration_status": integration_status or {},
            "used_gemini": bool(getattr(getattr(response, "strategy", None), "used_gemini", False)),
        }
    )
    return data


def dict_to_agent_response(data: Dict[str, Any]) -> AgentResponse:
    state_data = data.get("state") if isinstance(data.get("state"), dict) else {}
    strategy_data = data.get("strategy") if isinstance(data.get("strategy"), dict) else {}
    state = HumanState(**_filter_kwargs(HumanState, state_data))
    # Provide safe defaults so AgentStrategy can be built even when the remote
    # runtime (e.g. Agent Engine) returns a minimal payload with no strategy dict.
    _strategy_defaults: Dict[str, Any] = {
        "advice_mode": "OFF",
        "listening_mode": True,
        "speech_density": "LOW",
        "pause_length": "LONG",
        "emotional_tone": "Calm",
        "goal": "Listening",
        "pressure_level": "VERY_LOW",
    }
    _strategy_defaults.update(_filter_kwargs(AgentStrategy, strategy_data))
    strategy = AgentStrategy(**_strategy_defaults)
    mode = _mode_from_value(data.get("mode"))

    response = AgentResponse(
        text=str(data.get("text") or ""),
        state=state,
        mode=mode,
        strategy=strategy,
        scenario_id=data.get("scenario_id"),
        pressure_level=str(data.get("pressure_level") or getattr(strategy, "pressure_level", "MEDIUM")),
        facs_hint=list(data.get("facs_hint") or []),
        baseline_diff=list(data.get("baseline_diff") or []),
        care_proposal=str(data.get("care_proposal") or ""),
        staff_note=str(data.get("staff_note") or ""),
        handoff_note=str(data.get("handoff_note") or ""),
        intake_summary=str(data.get("intake_summary") or ""),
        intake_active=bool(data.get("intake_active", False)),
        red_flags=list(data.get("red_flags") or []),
        red_flag=dict(data.get("red_flag") or {}),
        asurada_state=dict(data.get("asurada_state") or {}),
    )
    return response


def _enum_name(value: Any) -> str:
    if isinstance(value, Enum):
        return value.name
    return str(value or "")


def _mode_from_value(value: Any) -> Mode:
    if isinstance(value, Mode):
        return value
    if isinstance(value, str):
        cleaned = value.split(".")[-1]
        if cleaned in Mode.__members__:
            return Mode[cleaned]
    return getattr(Mode, "QUIET_SUPPORT", next(iter(Mode)))


def _filter_kwargs(cls: Any, data: Dict[str, Any]) -> Dict[str, Any]:
    fields = getattr(cls, "__dataclass_fields__", {})
    return {key: value for key, value in data.items() if key in fields}
