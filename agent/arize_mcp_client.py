import asyncio
import json
import logging
import os
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Write-type tool candidates (use provided payload)
TOOL_CANDIDATES_WRITE = [
    "record_trace",
    "create_trace",
    "log_trace",
    "ingest_trace",
    "evaluate_trace",
    "create_dataset",
    "log_span",
]

# Read-type tool candidates (use empty/minimal payload)
TOOL_CANDIDATES_READ = [
    "list_projects",
    "get_projects",
    "list_traces",
    "get_traces",
    "list_spans",
    "get_spans",
    "list_prompts",
    "get_prompts",
    "list_datasets",
    "get_datasets",
    "list_experiments",
    "get_experiments",
    "list_sessions",
    "get_sessions",
    "list_annotation_configs",
    "list_models",
    "get_models",
]

# Combined for backward-compat
TOOL_CANDIDATES = TOOL_CANDIDATES_WRITE + TOOL_CANDIDATES_READ


async def call_arize_mcp_async(payload: Dict[str, Any]) -> Dict[str, Any]:
    command = os.getenv("ARIZE_MCP_COMMAND")
    if not command:
        return {"status": "disabled", "reason": "ARIZE_MCP_COMMAND is not set"}

    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        args = _load_args()
        env = _mcp_env()
        server_params = StdioServerParameters(command=command, args=args, env=env)

        async with AsyncExitStack() as stack:
            read, write = await stack.enter_async_context(stdio_client(server_params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            tools_result = await session.list_tools()
            tool_names = _tool_names(tools_result)
            selected = _select_tool(tool_names)
            if not selected:
                logger.warning("Arize MCP: no matching tool found. Available: %s", tool_names)
                return {"status": "missing_tool", "available_tools": tool_names}
            # Use empty args for read-type tools to avoid validation errors
            call_args = _build_call_args(selected, payload, tools_result)
            result = await session.call_tool(selected, call_args)
            return {
                "status": "called",
                "tool": selected,
                "available_tools": tool_names,
                "result": _jsonable_tool_result(result),
            }
    except Exception as exc:
        logger.exception("Arize MCP runtime call failed")
        return {"status": "failed", "error": str(exc)}


def call_arize_mcp(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(call_arize_mcp_async(payload))
    logger.warning("Arize MCP sync wrapper called inside a running event loop; skipping runtime call.")
    return {"status": "failed", "error": "running event loop"}


def _load_args() -> List[str]:
    raw = os.getenv("ARIZE_MCP_ARGS_JSON", "[]")
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        logger.warning("ARIZE_MCP_ARGS_JSON is not valid JSON; using no args.")
    return []


def _mcp_env() -> Dict[str, str]:
    env = dict(os.environ)
    for name in ["ARIZE_API_KEY", "ARIZE_SPACE_ID", "PHOENIX_COLLECTOR_ENDPOINT"]:
        value = os.getenv(name)
        if value:
            env[name] = value
    return env


def _tool_names(tools_result: Any) -> List[str]:
    tools = getattr(tools_result, "tools", tools_result)
    names = []
    for tool in tools or []:
        name = getattr(tool, "name", None)
        if name:
            names.append(name)
        elif isinstance(tool, dict) and tool.get("name"):
            names.append(str(tool["name"]))
    return names


def _select_tool(tool_names: List[str]) -> str:
    # 1. Respect explicit env override
    requested = os.getenv("ARIZE_MCP_TOOL_NAME")
    if requested and requested in tool_names:
        return requested
    if requested:
        logger.warning("ARIZE_MCP_TOOL_NAME=%s not in available tools: %s", requested, tool_names)
    # 2. Try read-type candidates first (safer — no required args usually)
    for candidate in TOOL_CANDIDATES_READ:
        if candidate in tool_names:
            return candidate
    # 3. Try write-type candidates
    for candidate in TOOL_CANDIDATES_WRITE:
        if candidate in tool_names:
            return candidate
    # 4. Last resort: pick first available tool
    if tool_names:
        logger.info("No known candidate matched; using first available tool: %s", tool_names[0])
        return tool_names[0]
    return ""


def _build_call_args(tool_name: str, fallback_payload: Dict[str, Any], tools_result: Any) -> Dict[str, Any]:
    """Build safe arguments for call_tool based on the tool's input schema."""
    # Inspect schema to find required fields
    tools = getattr(tools_result, "tools", tools_result) or []
    for tool in tools:
        name = getattr(tool, "name", None)
        if name != tool_name:
            continue
        schema = getattr(tool, "inputSchema", None)
        if not schema:
            return {}
        if isinstance(schema, dict):
            required = schema.get("required") or []
            props = schema.get("properties") or {}
            if not required:
                # No required args — pass empty dict to avoid validation errors
                return {}
            # Build minimal payload with only required fields
            minimal: Dict[str, Any] = {}
            for field in required:
                if field in fallback_payload:
                    minimal[field] = fallback_payload[field]
                elif field in props:
                    # Use a safe default based on type hint
                    field_type = props[field].get("type", "string")
                    minimal[field] = "" if field_type == "string" else None
            return minimal
    # No schema info — use empty dict (safer than passing unknown keys)
    return {}


def _jsonable_tool_result(result: Any) -> Any:
    if hasattr(result, "model_dump"):
        return result.model_dump()
    if hasattr(result, "dict"):
        return result.dict()
    return str(result)
