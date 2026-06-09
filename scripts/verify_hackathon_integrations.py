import argparse
import importlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check_import(name: str) -> bool:
    try:
        importlib.import_module(name)
        print(f"OK import {name}")
        return True
    except Exception as exc:
        print(f"FAIL import {name}: {exc}")
        return False


def check_code_markers() -> bool:
    markers = {
        "generate_content": False,
        "agent_engines_or_reasoning_engines": False,
        "ClientSession": False,
        "call_tool": False,
    }
    for path in list((ROOT / "agent").glob("*.py")) + list((ROOT / "scripts").glob("*.py")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        markers["generate_content"] |= "generate_content" in text
        markers["agent_engines_or_reasoning_engines"] |= "agent_engines" in text or "reasoning_engines" in text
        markers["ClientSession"] |= "ClientSession" in text
        markers["call_tool"] |= "call_tool" in text
    for marker, found in markers.items():
        print(f"{'OK' if found else 'FAIL'} marker {marker}")
    return all(markers.values())


def offline() -> int:
    checks = [
        check_import("google.generativeai"),
        check_import("vertexai"),
        check_import("mcp"),
        check_import("opentelemetry"),
        check_import("agent.gemini_brain"),
        check_import("agent.agent_engine_client"),
        check_import("agent.arize_mcp_client"),
        check_import("agent.hackathon_integrations"),
        check_code_markers(),
    ]
    return 0 if all(checks) else 1


def online() -> int:
    failed = False
    from agent.gemini_brain import GeminiBrain

    brain = GeminiBrain()
    if brain.is_available:
        result = brain._call_gemini("Reply with exactly: NAOMI Gemini online check")
        print(f"Gemini: {'OK' if result else 'FAIL'}")
        failed |= not bool(result)
    else:
        print("Gemini: SKIPPED; GEMINI_API_KEY/GOOGLE_API_KEY not set")
        failed = True

    if os.getenv("NAOMI_AGENT_ENGINE_RESOURCE"):
        from agent.agent_engine_client import query_agent_engine

        try:
            result = query_agent_engine("NAOMI Agent Engine online check", {})
            print(f"Agent Engine: {'OK' if result else 'FAIL'}")
            failed |= not bool(result)
        except Exception as exc:
            print(f"Agent Engine: FAIL {exc}")
            failed = True
    else:
        print("Agent Engine: SKIPPED; NAOMI_AGENT_ENGINE_RESOURCE not set")
        failed = True

    if os.getenv("ARIZE_MCP_COMMAND"):
        from agent.arize_mcp_client import call_arize_mcp

        result = call_arize_mcp({"trace_id": "verify-online", "text": "NAOMI Arize MCP online check"})
        available_tools = result.get("available_tools") or []
        list_tools_ok = result.get("status") in {"called", "missing_tool"} or bool(available_tools)
        call_tool_ok = result.get("status") == "called"
        print(f"Arize MCP list_tools: {'OK' if list_tools_ok else 'FAIL'}")
        print(f"Arize MCP call_tool: {'OK' if call_tool_ok else 'FAIL'}")
        if available_tools:
            print(f"Arize MCP available tools: {', '.join(available_tools)}")
        if result.get("tool"):
            print(f"Arize MCP selected tool: {result.get('tool')}")
        if not call_tool_ok:
            print(f"Arize MCP result: {result}")
        failed |= not (list_tools_ok and call_tool_ok)
    else:
        print("Arize MCP list_tools: SKIPPED; ARIZE_MCP_COMMAND not set")
        print("Arize MCP call_tool: SKIPPED; ARIZE_MCP_COMMAND not set")
        failed = True

    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--online", action="store_true")
    args = parser.parse_args()
    if args.online:
        return online()
    return offline()


if __name__ == "__main__":
    raise SystemExit(main())
