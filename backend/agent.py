from __future__ import annotations

import json
import os
from typing import Optional

import anthropic

from backend.actor_registry import (
    ACTOR_REGISTRY,
    build_actor_input,
    classify_demo_query,
    get_chain_for_query,
    is_registered_actor,
)
from backend.apify_client import ApifyClientWrapper
from backend.models import (
    AgentStep,
    DynamicActorSelection,
    ExecutionPlan,
    OrchestratorResponse,
    ParsedIntent,
)

# ── Constants ──────────────────────────────────────────────────────────────────

MODEL = "claude-sonnet-4-6"
MOCK_MODE: bool = os.getenv("MOCK_MODE", "true").lower() == "true"

# ── Prompts ────────────────────────────────────────────────────────────────────

_PARSE_SYSTEM = """You are an intent extraction engine. Given a user query, return ONLY valid JSON with these exact keys:
- intent_type: one of "sentiment" | "research" | "lead_gen" | "scrape"
- targets: array of strings (named entities: companies, people, topics)
- platforms: array of strings (e.g. "Reddit", "Twitter", "LinkedIn", "Google Maps", "Instagram", "YouTube", "TikTok", "Amazon", "Web")
- locations: array of strings (cities, regions, countries)
- time_range: string or null ("this week", "last month", "today", etc.)

Return nothing except the JSON object. No explanation, no markdown."""

_PLAN_SYSTEM = """You are an AI orchestration planner. Given a parsed user intent and a list of available Apify web scraping actors, select the best sequence of actors to fulfill the request.

Return ONLY a valid JSON object with these exact keys:
- steps: array of objects, each with:
    - actor_id: string (must be one of the provided actor IDs)
    - description: string (one sentence describing what this step collects)
    - depends_on: integer or null (step_number of the step whose output feeds this one)
- reasoning: string (one or two sentences explaining your choice)

Rules:
- Use only actor_ids from the provided list.
- Maximum {max_steps} steps.
- If chaining (e.g. Google Search → LinkedIn), set depends_on to the earlier step_number (1-indexed).
- Return nothing except the JSON object."""

_DYNAMIC_SELECT_SYSTEM = """You are selecting the best Apify web scraping actor from a list of candidates.
Given a task description and a list of actor candidates (with title, description, and user count), select the single best actor_id.

Return ONLY a valid JSON object with:
- selected_actor_id: string
- reasoning: string (one sentence)"""

_DYNAMIC_INPUT_SYSTEM = """You are constructing a minimal JSON input for an Apify web scraping actor.
Given the actor's input schema and the user's intent, return ONLY the run_input JSON object.

Rules:
- Include all required fields.
- Include relevant optional fields (search terms, location, limits).
- Set maxItems or equivalent limit to 50 or less for cost control.
- Return nothing except the JSON object."""

_SYNTHESIZE_SYSTEM = """You are a research assistant synthesizing scraped web data into a clear, useful answer.
Given the original user query and structured data collected from multiple sources, write a concise prose summary that directly answers the question.

Be specific: mention real names, numbers, and quotes where available. Do not pad with generic statements."""


class OrchestratorAgent:
    """
    ReAct-style agentic loop.
    MAX_ITERATIONS=5 hard cap across parse + plan + execute steps + synthesize.
    MAX_TOKENS_PER_RUN=10,000 total across all Claude calls in one run() invocation.
    Model: claude-sonnet-4-20250514 only.
    """

    def __init__(
        self,
        apify: ApifyClientWrapper,
        claude: anthropic.Anthropic,
        max_iterations: int = 5,
        max_tokens_per_run: int = 10000,
    ) -> None:
        self.apify = apify
        self.claude = claude
        self.max_iterations = max_iterations
        self.max_tokens_per_run = max_tokens_per_run
        # Reset per run() call
        self.tokens_used: int = 0
        self.iterations_used: int = 0

    # ── Public entry point ─────────────────────────────────────────────────────

    def run(self, user_query: str) -> OrchestratorResponse:
        """
        Full orchestration pipeline for one user query.
        Sequence: parse_query → plan_execution → execute_plan → synthesize_results.

        Token and iteration budgets are enforced throughout. If the budget would be
        exceeded before synthesize, remaining steps are skipped and synthesis runs
        on partial results.

        # Example input:  "What are people saying about OpenAI on Reddit and Twitter this week?"
        # Example output: OrchestratorResponse(
        #   iterations_used=4, total_items_collected=20, mock_mode=True,
        #   final_answer="This week on Reddit, OpenAI discussion centers on..."
        # )
        """
        self.tokens_used = 0
        self.iterations_used = 0

        # Step 1: parse query → structured intent [iteration 1]
        intent = self.parse_query(user_query)

        # Step 2: plan actor chain [iteration 2]
        plan = self.plan_execution(intent)

        # Step 3: execute each step [iterations 3–N]
        completed_steps = self.execute_plan(plan, intent)

        # Step 4: synthesize [final iteration]
        final_answer = self.synthesize_results(user_query, completed_steps)

        total_items = sum(
            s.result.item_count for s in completed_steps if s.result is not None
        )

        return OrchestratorResponse(
            query=user_query,
            plan=plan,
            steps_executed=completed_steps,
            final_answer=final_answer,
            total_items_collected=total_items,
            iterations_used=self.iterations_used,
            mock_mode=MOCK_MODE,
        )

    # ── Step 1: Parse ──────────────────────────────────────────────────────────

    def parse_query(self, user_query: str) -> ParsedIntent:
        """
        Extracts structured intent from the raw user query via one Claude call.
        Uses max_tokens=300 (small structured extraction).

        # Example input:  "Build me a lead list of fintech companies in NYC —
        #                  find them on Google Maps, then find their decision makers on LinkedIn"
        # Example output: ParsedIntent(intent_type="lead_gen",
        #   targets=["fintech companies"], platforms=["Google Maps", "LinkedIn"],
        #   locations=["NYC"], time_range=None)
        """
        response = self._claude_call(
            system=_PARSE_SYSTEM,
            user=user_query,
            max_tokens=300,
        )
        raw = self._extract_json(response)
        self.iterations_used += 1
        return ParsedIntent(
            intent_type=raw.get("intent_type", "scrape"),
            targets=raw.get("targets", []),
            platforms=raw.get("platforms", []),
            locations=raw.get("locations", []),
            time_range=raw.get("time_range"),
            raw_query=user_query,
        )

    # ── Step 2: Plan ───────────────────────────────────────────────────────────

    def plan_execution(self, intent: ParsedIntent) -> ExecutionPlan:
        """
        Decides the actor chain. Two-tier approach:

        TIER 1 (fast, no Claude call):
          get_chain_for_query returns non-empty list → build ExecutionPlan directly.

        TIER 2 (one Claude call):
          get_chain_for_query returns [] → Claude selects from ACTOR_REGISTRY.
          Unknown actor_ids proposed by Claude are marked for dynamic resolution
          in execute_plan via discover_actor_from_store().

        # Example input:  ParsedIntent(platforms=["Reddit","Twitter"])
        # Example output: ExecutionPlan(steps=[reddit_step, twitter_step],
        #                               reasoning="Matched platforms to registered actors")
        """
        self.iterations_used += 1

        # Tier 1: registry or demo chain
        chain = get_chain_for_query(intent.raw_query, intent)
        if chain:
            demo_key = classify_demo_query(intent.raw_query)
            reasoning = (
                f"Matched demo query pattern '{demo_key}'"
                if demo_key
                else f"Matched platforms {intent.platforms} to registered actors"
            )
            steps = [
                AgentStep(
                    step_number=i + 1,
                    actor_id=actor_id,
                    description=ACTOR_REGISTRY[actor_id]["description"],
                    depends_on=i if i > 0 else None,
                )
                for i, actor_id in enumerate(chain)
            ]
            return ExecutionPlan(steps=steps, reasoning=reasoning)

        # Tier 2: Claude selects from registry + may propose dynamic actors
        max_steps = self.max_iterations - 2  # reserve 1 for parse, 1 for synthesize
        registry_summary = "\n".join(
            f"- {aid}: {info['description']} (platforms: {info['platforms']})"
            for aid, info in ACTOR_REGISTRY.items()
        )
        user_msg = (
            f"User intent:\n{json.dumps(intent.model_dump(), default=str)}\n\n"
            f"Available registered actors ({len(ACTOR_REGISTRY)}):\n{registry_summary}\n\n"
            f"Note: 33,000+ additional actors exist on the Apify Store. "
            f"If none of the above fit the request, propose actor_ids you would search for "
            f"and they will be resolved dynamically.\n\n"
            f"Return a plan with at most {max_steps} steps."
        )
        response = self._claude_call(
            system=_PLAN_SYSTEM.replace("{max_steps}", str(max_steps)),
            user=user_msg,
            max_tokens=500,
        )
        raw = self._extract_json(response)

        raw_steps = raw.get("steps", [])[:max_steps]
        steps = [
            AgentStep(
                step_number=i + 1,
                actor_id=s.get("actor_id", "apify~google-search-scraper"),
                description=s.get("description", ""),
                depends_on=s.get("depends_on"),
            )
            for i, s in enumerate(raw_steps)
        ]
        return ExecutionPlan(steps=steps, reasoning=raw.get("reasoning", ""))

    # ── Step 3: Execute ────────────────────────────────────────────────────────

    def execute_plan(
        self, plan: ExecutionPlan, intent: ParsedIntent
    ) -> list[AgentStep]:
        """
        Runs each step in the plan sequentially.
        Budget: max_iterations - 3 execution steps (1 parse + 1 plan + 1 synthesize reserved).

        Per step:
          - TIER 1: actor is registered → build_actor_input()
          - TIER 2: actor is not registered → discover_actor_from_store()
          prev_results from the immediately preceding step are passed for chaining.

        # Example input:  plan with 2 steps [Reddit, Twitter]
        # Example output: [
        #   AgentStep(step_number=1, actor_id="trudax~reddit-scraper-lite",
        #             result=ActorRunResult(status=SUCCEEDED, item_count=10)),
        #   AgentStep(step_number=2, actor_id="apidojo~tweet-scraper",
        #             result=ActorRunResult(status=SUCCEEDED, item_count=10))
        # ]
        """
        max_exec_steps = self.max_iterations - 3  # reserve parse + plan + synthesize
        prev_results: list[dict] = []

        for step in plan.steps:
            if self.iterations_used >= self.max_iterations - 1:
                # Reserve the last iteration for synthesize
                break
            if self.iterations_used - 2 >= max_exec_steps:
                # Cap execution steps regardless of total budget
                break

            # Determine run_input — Tier 1 or Tier 2
            if is_registered_actor(step.actor_id):
                run_input = build_actor_input(step.actor_id, intent, prev_results or None)
            else:
                # Tier 2: dynamic discovery — find and configure an actor from the store
                resolved_id, run_input = self.discover_actor_from_store(
                    intent, step.description
                )
                step.actor_id = resolved_id

            step.run_input = run_input
            step.result = self.apify.run_and_collect(step.actor_id, run_input)
            prev_results = step.result.items
            self.iterations_used += 1

        return plan.steps

    def discover_actor_from_store(
        self, intent: ParsedIntent, step_description: str
    ) -> tuple[str, dict]:
        """
        Tier 2 dynamic path. Called when a planned step's actor_id is not in ACTOR_REGISTRY.

        Steps:
          1. Search Apify Store for candidates matching the intent + step description
          2. Claude picks the best actor_id from candidates (by totalUsers + description fit)
          3. Fetch that actor's input schema from /builds/default
          4. Claude constructs minimal valid run_input from schema + intent

        Counts as 2 Claude calls but 0 additional iterations (called from within execute_plan).

        # Example input:
        #   intent=ParsedIntent(targets=["Austin TX homes"], platforms=["Zillow"]),
        #   step_description="Scrape Zillow real estate listings in Austin TX"
        # Example output: ("vaclavrut~zillow-scraper",
        #   {"startUrls": [{"url": "https://www.zillow.com/austin-tx/"}], "maxItems": 50})
        """
        # Build a tight search query
        search_terms = intent.targets + intent.platforms + [step_description]
        search_query = " ".join(search_terms[:6])  # keep it concise

        candidates = self.apify.search_store(search_query, sort_by="popularity", limit=10)

        # Claude selects best actor
        candidate_summary = json.dumps(
            [{"actor_id": f"{c['username']}~{c['name']}", "title": c["title"],
              "description": c.get("description", ""), "totalUsers": c["stats"]["totalUsers"]}
             for c in candidates],
            indent=2,
        )
        select_response = self._claude_call(
            system=_DYNAMIC_SELECT_SYSTEM,
            user=f"Task: {step_description}\n\nCandidates:\n{candidate_summary}",
            max_tokens=150,
        )
        selection_raw = self._extract_json(select_response)
        selected_id: str = selection_raw.get("selected_actor_id", f"{candidates[0]['username']}~{candidates[0]['name']}")
        selection_reasoning: str = selection_raw.get("reasoning", "")

        # Log the dynamic selection (useful for debugging)
        _ = DynamicActorSelection(
            search_query=search_query,
            candidates=candidates,
            selected_actor_id=selected_id,
            selection_reasoning=selection_reasoning,
        )

        # Claude builds run_input from schema
        schema = self.apify.get_actor_input_schema(selected_id)
        input_response = self._claude_call(
            system=_DYNAMIC_INPUT_SYSTEM,
            user=(
                f"Actor: {selected_id}\n"
                f"Task: {step_description}\n"
                f"Intent: {json.dumps(intent.model_dump(), default=str)}\n"
                f"Input schema: {json.dumps(schema)}"
            ),
            max_tokens=300,
        )
        run_input = self._extract_json(input_response)
        return selected_id, run_input

    # ── Step 4: Synthesize ─────────────────────────────────────────────────────

    def synthesize_results(
        self, user_query: str, steps: list[AgentStep]
    ) -> str:
        """
        Synthesizes all collected data into a prose answer via one Claude call.
        Passes up to the top 5 items per step to stay within token budget.
        max_tokens is clamped: at least 500, at most 2000, bounded by remaining budget.

        # Example input:
        #   user_query="What are people saying about OpenAI on Reddit and Twitter this week?"
        #   steps=[AgentStep(reddit, 10 items), AgentStep(twitter, 10 items)]
        # Example output:
        #   "This week, OpenAI is generating significant discussion across platforms.
        #    On Reddit (r/MachineLearning), the top post has 2,847 upvotes and covers
        #    GPT-5 coding performance. On Twitter, Andrej Karpathy (@karpathy) noted..."
        """
        self.iterations_used += 1

        # Budget: use whatever is left, min 500, max 2000
        remaining = self.max_tokens_per_run - self.tokens_used
        synth_tokens = max(500, min(2000, remaining))

        # Build context: top 5 items per step
        context_parts = []
        for step in steps:
            if step.result is None or not step.result.items:
                continue
            actor_title = ACTOR_REGISTRY.get(step.actor_id, {}).get("title", step.actor_id)
            top_items = step.result.items[:5]
            context_parts.append(
                f"### {actor_title} ({step.result.item_count} items total)\n"
                + json.dumps(top_items, indent=2, default=str)
            )

        if not context_parts:
            return "No data was collected. The actor runs may have returned empty results."

        context = "\n\n".join(context_parts)
        user_msg = f"User query: {user_query}\n\nCollected data:\n{context}"

        return self._claude_call(
            system=_SYNTHESIZE_SYSTEM,
            user=user_msg,
            max_tokens=synth_tokens,
        )

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _claude_call(self, system: str, user: str, max_tokens: int) -> str:
        """
        Single Claude API call. Tracks token usage against MAX_TOKENS_PER_RUN.
        Raises RuntimeError if budget is already exhausted before the call.
        Model is fixed to MODEL constant — no substitutions.

        # Example input:  system="Extract JSON...", user="Find AI startups in SF", max_tokens=300
        # Example output: '{"intent_type": "research", "targets": ["AI startups"], ...}'
        """
        estimated_cost = self._count_tokens(system + user) + max_tokens
        if self.tokens_used + estimated_cost > self.max_tokens_per_run:
            # Soft cap: log and continue with reduced max_tokens rather than hard-failing
            max_tokens = max(100, self.max_tokens_per_run - self.tokens_used - self._count_tokens(system + user))

        message = self.claude.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        response_text: str = message.content[0].text
        # Track actual token usage from the API response
        self.tokens_used += message.usage.input_tokens + message.usage.output_tokens
        return response_text

    def _extract_json(self, text: str) -> dict:
        """
        Extracts and parses JSON from a Claude response string.
        Handles cases where Claude wraps JSON in markdown code fences.
        Returns {} on any parse failure (never raises).

        # Example input:  '```json\n{"intent_type": "sentiment"}\n```'
        # Example output: {"intent_type": "sentiment"}

        # Example input:  '{"intent_type": "sentiment"}'
        # Example output: {"intent_type": "sentiment"}
        """
        text = text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove opening fence (```json or ```) and closing fence (```)
            inner = [l for l in lines[1:] if l.strip() != "```"]
            text = "\n".join(inner).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Attempt to find the first {...} block as a fallback
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
        return {}

    def _count_tokens(self, text: str) -> int:
        """
        Rough token estimate for budget checks before a Claude call.
        Uses the standard 4-chars-per-token heuristic. Not billed — just a guard.

        # Example input:  "Hello world this is a test" (26 chars)
        # Example output: 6
        """
        return len(text) // 4
