from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ActorRunStatus(str, Enum):
    # Maps to Apify's run status strings.
    # Note: Apify returns "TIMED-OUT" (hyphen); we normalize to TIMED_OUT here.
    READY = "READY"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    ABORTED = "ABORTED"


class ActorCandidate(BaseModel):
    # Constructed from a /v2/store response item.
    # Example input:  {"id": "HDSasDasz...", "username": "apify", "name": "google-search-scraper",
    #                  "title": "Google Search Scraper", "description": "Crawls Google SERPs",
    #                  "stats": {"totalUsers": 80000},
    #                  "currentPricingInfo": {"pricingModel": "PRICE_PER_DATASET_ITEM"}}
    # Example output: ActorCandidate(actor_id="apify~google-search-scraper",
    #                                title="Google Search Scraper", total_users=80000, ...)
    actor_id: str                   # "username~actor-name" form, e.g. "apify~google-search-scraper"
    title: str
    description: str
    total_users: int                # from stats.totalUsers — primary popularity signal
    pricing_model: str              # "FREE" | "PRICE_PER_DATASET_ITEM" | "FLAT_PRICE_PER_MONTH" | etc.


class ActorRunResult(BaseModel):
    # Populated after a run completes (poll_run_until_done + fetch_dataset_items).
    # Example input:  run finished with id="HG7ML7M8z78YcAPEB", status="SUCCEEDED",
    #                 defaultDatasetId="9RnDh0sFw1iyhSnEP", items=[{...}]
    # Example output: ActorRunResult(actor_id="apify~google-search-scraper",
    #                                status=SUCCEEDED, item_count=3, error_message=None)
    actor_id: str
    run_id: str
    status: ActorRunStatus
    dataset_id: str
    kv_store_id: str
    items: list[dict] = Field(default_factory=list)     # raw dataset items (JSON objects)
    error_message: Optional[str] = None                 # set when status != SUCCEEDED
    item_count: int = 0                                 # len(items); computed on assignment


class AgentStep(BaseModel):
    # One step in an execution plan. result is None until the step runs.
    # Example input:  step_number=1, actor_id="apify~google-search-scraper",
    #                 description="Search Google for AI startups in SF",
    #                 run_input={"queries": "AI startups San Francisco", "resultsPerPage": 10}
    # Example output: AgentStep with result=ActorRunResult(...) after execute_plan() fills it in
    step_number: int
    actor_id: str
    description: str                                    # human-readable label shown in UI
    run_input: dict = Field(default_factory=dict)       # exact JSON sent to Apify
    result: Optional[ActorRunResult] = None             # filled in by execute_plan()
    depends_on: Optional[int] = None                    # step_number whose items feed this step's input


class ExecutionPlan(BaseModel):
    # Output of plan_execution(). Contains ordered steps + Claude's reasoning.
    # Example input:  intent targets Reddit + Twitter sentiment about OpenAI
    # Example output: ExecutionPlan(steps=[reddit_step, twitter_step],
    #                               reasoning="Query targets Reddit and Twitter; using registered actors")
    steps: list[AgentStep]
    reasoning: str                                      # why these actors were chosen


class ParsedIntent(BaseModel):
    # Structured intent extracted from the raw user query by parse_query().
    # Example input:  "What are people saying about OpenAI on Reddit and Twitter this week?"
    # Example output: ParsedIntent(intent_type="sentiment", targets=["OpenAI"],
    #                              platforms=["Reddit", "Twitter"], time_range="this week")
    intent_type: str                                    # "sentiment" | "research" | "lead_gen" | "scrape"
    targets: list[str]                                  # named entities: companies, people, topics
    platforms: list[str]                                # ["Reddit", "Twitter", "LinkedIn", ...]
    locations: list[str]                                # ["San Francisco", "NYC", ...]
    time_range: Optional[str] = None                    # "this week" | "last month" | None
    raw_query: str                                      # original user query, passed through unchanged


class DynamicActorSelection(BaseModel):
    # Result of the Tier 2 dynamic discovery path (agent.discover_actor_from_store).
    # Example input:  user asks about Zillow listings; no registry actor matches
    # Example output: DynamicActorSelection(
    #   search_query="zillow real estate scraper",
    #   candidates=[{"actor_id": "some_user~zillow-scraper", "title": "...", "total_users": 12400}],
    #   selected_actor_id="some_user~zillow-scraper",
    #   selection_reasoning="Highest totalUsers (12,400) and description matches real estate scraping"
    # )
    search_query: str                                   # sent to GET /v2/store?search=...
    candidates: list[dict]                              # top store results (title, actor_id, totalUsers)
    selected_actor_id: str                              # Claude's pick
    selection_reasoning: str                            # Claude's explanation


class OrchestratorRequest(BaseModel):
    # HTTP request body for POST /orchestrate.
    # Example input:  {"user_query": "Build me a lead list of fintech companies in NYC..."}
    # Example output: OrchestratorRequest(user_query="Build me a lead list...")
    user_query: str


class OrchestratorResponse(BaseModel):
    # HTTP response body for POST /orchestrate.
    # Example input:  completed agent run with 2 steps, 20 total items, 4 iterations
    # Example output: OrchestratorResponse(query="What are people saying...",
    #                                      iterations_used=4, total_items_collected=20,
    #                                      mock_mode=True, final_answer="This week on Reddit...")
    query: str
    plan: ExecutionPlan
    steps_executed: list[AgentStep]                     # AgentStep list with result fields populated
    final_answer: str                                   # Claude's synthesized prose summary
    total_items_collected: int                          # sum of item_count across all steps
    iterations_used: int                                # how many of MAX_ITERATIONS=5 were consumed
    mock_mode: bool                                     # True when MOCK_MODE env var is "true"
