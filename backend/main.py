from __future__ import annotations

import os

import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.agent import OrchestratorAgent
from backend.apify_client import ApifyClientWrapper
from backend.models import OrchestratorRequest, OrchestratorResponse

# ── Environment ────────────────────────────────────────────────────────────────

MOCK_MODE: bool = os.getenv("MOCK_MODE", "true").lower() == "true"
APIFY_TOKEN: str = os.getenv("APIFY_TOKEN", "")
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Apify Actor Orchestrator",
    version="1.0.0",
    description="AI agent that selects and chains Apify actors to answer natural language queries.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # frontend is served as a local file; restrict in production
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── Shared clients (created once at startup) ───────────────────────────────────

_apify = ApifyClientWrapper()
_claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# ── Routes ─────────────────────────────────────────────────────────────────────


@app.get("/health")
def health() -> dict:
    """
    Liveness check. Returns server status, mock mode flag, and version.

    # Example input:  GET /health
    # Example output: {"status": "ok", "mock_mode": true, "version": "1.0.0"}
    """
    return {
        "status": "ok",
        "mock_mode": MOCK_MODE,
        "version": app.version,
    }


@app.post("/orchestrate", response_model=OrchestratorResponse)
def orchestrate(request: OrchestratorRequest) -> OrchestratorResponse:
    """
    Main endpoint. Accepts a natural language query, runs the full ReAct agent
    loop (parse → plan → execute → synthesize), and returns structured results.

    Raises 400 if user_query is blank.
    Raises 500 (with detail) if the agent throws an unexpected exception.

    # Example input:
    #   POST /orchestrate
    #   {"user_query": "What are people saying about OpenAI on Reddit and Twitter this week?"}
    # Example output:
    #   OrchestratorResponse(
    #     query="What are people saying...",
    #     iterations_used=4,
    #     total_items_collected=20,
    #     mock_mode=True,
    #     final_answer="This week on Reddit, discussion about OpenAI centers on..."
    #   )
    """
    query = request.user_query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="user_query must not be blank")

    agent = OrchestratorAgent(apify=_apify, claude=_claude)
    try:
        return agent.run(query)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
