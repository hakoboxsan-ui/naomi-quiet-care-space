import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)
_tracer = None
_configured = False


def get_tracer():
    global _configured, _tracer
    if _configured:
        return _tracer
    _configured = True

    endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT")
    if not endpoint:
        _tracer = None
        return None

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(resource=Resource.create({"service.name": "naomi-quiet-care-space"}))
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("naomi.hackathon")
    except Exception:
        logger.exception("Phoenix OpenTelemetry tracing setup failed")
        _tracer = None
    return _tracer


def trace_naomi_turn(payload: Dict[str, Any]) -> Dict[str, Any]:
    tracer = get_tracer()
    if tracer is None:
        return {"status": "disabled", "reason": "PHOENIX_COLLECTOR_ENDPOINT is not set"}

    try:
        with tracer.start_as_current_span("naomi.process_turn") as span:
            status = payload.get("integration_status", {})
            span.set_attribute("naomi.input_length", int(payload.get("input_length", 0)))
            span.set_attribute("naomi.mode", str(payload.get("mode", "")))
            span.set_attribute("naomi.pressure_level", str(payload.get("pressure_level", "")))
            span.set_attribute("naomi.used_gemini", bool(payload.get("used_gemini", False)))
            span.set_attribute("naomi.used_agent_engine", status.get("agent_engine") == "called")
            span.set_attribute("naomi.used_arize_mcp", status.get("arize_mcp") == "called")
            span.set_attribute("naomi.has_staff_note", bool(payload.get("staff_note")))
            span.set_attribute("naomi.red_flag_triggered", bool((payload.get("red_flag") or {}).get("triggered")))
            span.set_attribute("naomi.trace_id", str(payload.get("trace_id", "")))
        return {"status": "sent"}
    except Exception as exc:
        logger.exception("Phoenix OpenTelemetry trace failed")
        return {"status": "failed", "error": str(exc)}
