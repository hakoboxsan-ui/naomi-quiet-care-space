import os
import sys

from agent.agent_engine_app import NaomiAgentEngineApp


def main() -> int:
    project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION") or os.getenv("GOOGLE_CLOUD_REGION") or "us-central1"
    staging_bucket = os.getenv("VERTEX_AI_STAGING_BUCKET")

    if not project or not staging_bucket:
        print("Set GOOGLE_CLOUD_PROJECT and VERTEX_AI_STAGING_BUCKET before deploying.", file=sys.stderr)
        return 1

    import vertexai

    vertexai.init(project=project, location=location, staging_bucket=staging_bucket)
    app = NaomiAgentEngineApp()

    try:
        from vertexai import agent_engines

        remote = agent_engines.create(
            app,
            requirements=[
                "google-generativeai",
                "python-dotenv",
                "google-cloud-aiplatform",
            ],
            display_name="naomi-quiet-care-space",
            description="NAOMI quiet care Agent Engine runtime",
        )
    except Exception as first_exc:
        print(f"agent_engines.create failed, trying reasoning_engines: {first_exc}", file=sys.stderr)
        from vertexai.preview import reasoning_engines

        remote = reasoning_engines.ReasoningEngine.create(
            app,
            requirements=[
                "google-generativeai",
                "python-dotenv",
                "google-cloud-aiplatform",
            ],
            display_name="naomi-quiet-care-space",
            description="NAOMI quiet care Agent Engine runtime",
        )

    resource_name = getattr(remote, "resource_name", None) or getattr(remote, "name", None) or str(remote)
    print(resource_name)
    print("Set NAOMI_AGENT_ENGINE_RESOURCE to this value in Cloud Run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
