"""Deploy NAOMI Agent Engine to Vertex AI.

The app class is defined INLINE in __main__ scope so that cloudpickle
embeds the full class definition in the pickle — the remote container
does NOT need to import any local NAOMI module to deserialize it.
"""
import os
import sys


# ---------------------------------------------------------------------------
# Inline app class (defined in __main__, so cloudpickle inlines it)
# ---------------------------------------------------------------------------

class NaomiRemoteApp:
    """Minimal self-contained Reasoning Engine app.

    Rules:
    - No imports from local agent.* modules at class / __init__ level.
    - set_up() is called by the Agent Engine runtime after deserialization.
    - query() is the public entry point.
    """

    def set_up(self):
        """Called by Agent Engine runtime after unpickling. Must not raise."""
        pass

    def __init__(self):
        pass

    def query(self, input="", profile=None):
        text = str(input or "")
        response = self._safe_respond(text)
        return {
            "text": response,
            "input": text,
            "used_runtime": "agent_engine",
            "integration_status": {"agent_engine": "called"},
            "state": "CALM",
            "mode": "SUPPORT",
        }

    def process_free_chat(self, input="", profile=None):
        return self.query(input=input, profile=profile)

    def _safe_respond(self, text):
        try:
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            if api_key:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-2.5-flash")
                result = model.generate_content(
                    f"You are NAOMI, a calm listening AI. Reply briefly in Japanese to: {text}"
                )
                return result.text
        except Exception:
            pass
        return "少し聞かせてください。（Agent Engine 経由）"


# ---------------------------------------------------------------------------

def main() -> int:
    project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION") or os.getenv("GOOGLE_CLOUD_REGION") or "us-central1"
    staging_bucket = os.getenv("VERTEX_AI_STAGING_BUCKET")

    if not project or not staging_bucket:
        print("Set GOOGLE_CLOUD_PROJECT and VERTEX_AI_STAGING_BUCKET before deploying.", file=sys.stderr)
        return 1

    import vertexai

    vertexai.init(project=project, location=location, staging_bucket=staging_bucket)

    app = NaomiRemoteApp()

    reqs = [
        "google-generativeai",
        "python-dotenv",
        "google-cloud-aiplatform",
    ]

    # Try newer agent_engines API first, fall back to reasoning_engines
    remote = None
    try:
        from vertexai import agent_engines
        print("Trying agent_engines.create ...", file=sys.stderr)
        remote = agent_engines.create(
            app,
            requirements=reqs,
            display_name="naomi-quiet-care-space",
            description="NAOMI quiet care Agent Engine runtime",
        )
    except Exception as first_exc:
        print(f"agent_engines.create failed: {first_exc}", file=sys.stderr)
        print("Falling back to reasoning_engines.ReasoningEngine.create ...", file=sys.stderr)
        try:
            from vertexai.preview import reasoning_engines
            remote = reasoning_engines.ReasoningEngine.create(
                app,
                requirements=reqs,
                display_name="naomi-quiet-care-space",
                description="NAOMI quiet care Agent Engine runtime",
            )
        except Exception as second_exc:
            print(f"reasoning_engines.create also failed: {second_exc}", file=sys.stderr)
            return 1

    if remote is None:
        print("ERROR: no remote agent was created.", file=sys.stderr)
        return 1

    resource_name = getattr(remote, "resource_name", None) or getattr(remote, "name", None) or str(remote)
    print(resource_name)
    print("Set NAOMI_AGENT_ENGINE_RESOURCE to this value in Cloud Run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
