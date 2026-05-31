# Apify Actor Orchestrator — Project Reference

## Project Overview

An AI agent that accepts natural language queries, searches Apify's marketplace of 33,000+ Actors,
selects the right Actor(s), chains them when needed, executes them, and returns structured data
with a synthesized prose summary. A single-file React + Tailwind frontend wraps a FastAPI backend.

The system runs in MOCK_MODE by default so no Apify credits are consumed during development.
A single environment variable swap (`MOCK_MODE=false`) activates live mode on Sunday.

---

## Constraints

| Constraint | Value |
|---|---|
| `MOCK_MODE` | `true` until told otherwise |
| `MAX_ITERATIONS` | 5 (agent loop hard cap) |
| `MAX_TOKENS_PER_RUN` | 10,000 (total across all Claude calls per orchestration run) |
| Claude model | `claude-sonnet-4-6` — no substitutions |
| Build cadence | One file at a time — stop and wait for confirmation before the next file |
| Syntax check | `python -m py_compile` after every Python file; report errors before confirming |
| Function comments | Every function must have an inline example: real input → expected output |
| Unknown fields | Use `VERIFY_FIELD_NAME` placeholder + TODO comment — never guess silently |
| Mock data | Must use real company/person names, real-looking URLs, realistic post text |
| CLAUDE.md | Update build-status checkboxes after each file is completed |
| CLAUDE.md sync | ANY change to instructions, features, actor list, or constraints must ALSO be reflected in `CLAUDE.md` before stopping — it is the single source of truth for resuming sessions |
| Actor registry | 15 hardcoded actors are the **foundation**, not the ceiling. Ceiling is 33,000+ via live store search. This two-tier design must be preserved in `actor_registry.py` and `agent.py` at all times |

---

## File Structure

```
/apify-orchestrator
  CLAUDE.md                  ← this file (living reference, update after each build step)
  .env                       ← MOCK_MODE, APIFY_TOKEN, ANTHROPIC_API_KEY
  requirements.txt           ← Python dependencies
  README.md                  ← Quick-start, demo queries, Sunday checklist
  /backend
    models.py                ← Pydantic v2 models (no logic, no I/O)
    apify_client.py          ← Apify REST API wrapper + all mock fixtures
    actor_registry.py        ← Curated actor catalog, demo-query classifier, input builder
    agent.py                 ← ReAct agentic loop (MAX_ITERATIONS=5)
    main.py                  ← FastAPI app (/health, /orchestrate)
  /frontend
    index.html               ← Single-file React+Tailwind+Babel CDN UI (no build step)
```

---

## Build Status

- [x] FILE 0: `CLAUDE.md`
- [x] FILE 1: `backend/models.py`
- [x] FILE 2: `backend/apify_client.py`
- [x] FILE 3: `backend/actor_registry.py`
- [x] FILE 4: `backend/agent.py`
- [x] FILE 5: `backend/main.py`
- [x] FILE 6: `frontend/index.html` *(rewritten: marked.js markdown, pipeline step cards, animated loader, MOCK MODE banner, Vercel/Linear aesthetic; analysis section split into "RAW DATA OUTPUT" + "AGENT INSIGHTS" cards via `splitFinalAnswer()` — splits at last insights/next-steps heading or `---` rule)*
- [x] FILE 7: `.env`
- [x] FILE 8: `requirements.txt`
- [x] FILE 9: `README.md`
- [x] UX REDESIGN: Two-phase actor discovery + deferred AI summary *(frontend-only; no backend changes)*
  - **Phase 1** — on submit, `predictActorChain()` runs locally (JS port of Tier-1 backend classifier); `ActorDiscoveryPanel` shows one card per predicted actor (title, platform, description, ~N items). Two buttons: "Run these actors for me" → Phase 2; "I'll use these myself ↗" → opens `https://apify.com/[username]/[actor-name]` in new tabs
  - **Phase 2** — `/orchestrate` runs as before; execution pipeline shows immediately; synthesized output hidden behind "Generate AI Summary ▼" button
  - Embedded `ACTOR_REGISTRY_FRONTEND`, `DEMO_QUERY_CHAINS_JS`, `PLATFORM_ACTOR_MAP_JS` as frontend constants (exact mirrors of `actor_registry.py` Tier-1 data)
  - Phase 1 predicted actors verified to match Phase 2 execution pipeline for all 3 demo queries
- [x] RAILWAY DEPLOYMENT
  - `Procfile` added: `uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}`
  - `GET /` route added to `main.py` via `FileResponse("frontend/index.html")`
  - `API_BASE` changed from `"http://localhost:8000"` to `""` (relative paths) in `index.html`
- [x] BUG FIXES (today's session)
  - `agent.py` — Tier-1 plan no longer counts as an iteration (Reddit step was skipped in ai_startups_sf chain)
  - `agent.py` — Claude model ID updated from `claude-sonnet-4-20250514` (retired) → `claude-sonnet-4-6`
  - `apify_client.py` — lazy-import `apify_client` inside `__init__` only when `MOCK_MODE=false`; removed module-level `_SDK_AVAILABLE` flag that blocked Railway startup
  - `requirements.txt` — bumped `apify-client` to `1.9.2`, pinned `apify-shared==1.1.2`
  - `index.html` — analysis cards given explicit `overflow: visible`; `ResultPanel` keyed by `result.query` to reset `showSummary` state between queries

---

## V2 Roadmap

### Feature: Per-User Actor Personalization

**Description:**
Track which actors each user runs and surface their most-used actors as personalized fast-path options in Phase 1 discovery, shown above the default 15 hardcoded actors.

**Architecture notes:**

- **Database** — lightweight store (Supabase free tier or SQLite) with a `actor_runs` table:
  ```
  user_id       TEXT    -- derived from IP or session token
  actor_id      TEXT    -- e.g. "trudax~reddit-scraper-lite"
  query_text    TEXT    -- original user query
  run_timestamp INTEGER -- unix epoch
  success       BOOLEAN -- whether the run returned SUCCEEDED status
  ```

- **New backend endpoint** — `GET /user/actors`
  - Reads `user_id` from request header / session
  - Returns top 5 most-used `actor_id` strings for that user (ordered by run count desc)
  - Falls back to empty list for new users

- **`actor_registry.py`** — add `get_user_fast_path(user_id: str) -> list[str]`
  - Queries DB, returns personalized actor list
  - Called by the agent or directly by the new endpoint

- **Phase 1 UI (`ActorDiscoveryPanel`)** — if user history exists, prepend a
  `"YOUR FREQUENT ACTORS"` section (same card style) above `"RECOMMENDED ACTORS"`;
  actors sourced from `GET /user/actors` response

**Complexity estimate:** Medium (1–2 days)

**Dependencies:** Supabase free tier or SQLite, user session handling

---

## 3 Demo Queries + Actor Chains

### Query 1 — AI Startups SF
> "Find me the top AI startups in SF, their founders' LinkedIn profiles, and what people are saying about them on Reddit"

**Classifier key:** `ai_startups_sf`

**Chain:**
1. `apify~google-search-scraper` — finds LinkedIn profile URLs via SERP
2. `apimaestro~linkedin-profile-batch-scraper-no-cookies-required` — scrapes founder profiles (input field: `urls`)
3. `trudax~reddit-scraper-lite` — scrapes Reddit posts about the startups

**Iterations used:** 5 of 5 (parse + plan + 3 actor steps + synthesize fits exactly within budget)

---

### Query 2 — OpenAI Sentiment
> "What are people saying about OpenAI on Reddit and Twitter this week?"

**Classifier key:** `reddit_twitter_sentiment`

**Chain:**
1. `trudax~reddit-scraper-lite` — Reddit posts (input: `searches: ["OpenAI"]`)
2. `apidojo~tweet-scraper` — Tweets (input: `searchTerms: ["OpenAI"]`, `start: 7-days-ago`)
   - Actor numeric ID: `61RPP7dywgiy0JPD0` (from technical reference Section 6.5)
   - NOTE: `start`/`end` date params only work with `searchTerms` (confirmed in reference)

**Iterations used:** 4 of 5

---

### Query 3 — Fintech Lead Gen NYC
> "Build me a lead list of fintech companies in NYC — find them on Google Maps, then find their decision makers on LinkedIn"

**Classifier key:** `fintech_lead_gen`

**Chain:**
1. `compass~crawler-google-places` — NYC fintech companies (input: `searchStringsArray`, `locationQuery`)
2. `harvestapi~linkedin-company-employees` — decision makers (input field: `companyUrls`, `mode: "Short"`)

**Iterations used:** 4 of 5

---

## Two-Tier Actor Architecture

**This design must be preserved in `actor_registry.py` and `agent.py` at all times.**

```
TIER 1 — ACTOR_REGISTRY (15 hardcoded actors) = FOUNDATION
  └── Fast path: no extra API calls needed
  └── Input built by hardcoded per-actor logic in build_actor_input()
  └── Used when: demo query matches, OR intent.platforms maps to a registered actor

TIER 2 — Dynamic store search (33,000+ actors) = CEILING
  └── Triggered when get_chain_for_query() returns [] (no registry match)
  └── agent.py calls search_store() → Claude picks best actor → get_actor_input_schema()
      → Claude builds minimal run_input from schema
  └── Slower: 2 extra API calls + 2 extra Claude calls per dynamic step
```

The 15 registered actors are **not** an exhaustive list — they are a curated fast lane for the most common scraping tasks. Any query the registry can't handle falls through to the full Apify Store automatically.

---

## All 15 Registered Actors (Tier 1 Foundation)

| # | Actor ID | Platforms | Section |
|---|---|---|---|
| 1 | `apify~google-search-scraper` | Google, SERP | 6.3 |
| 2 | `apify~website-content-crawler` | Web | 6.1 |
| 3 | `apify~web-scraper` | Web (custom JS) | 6.2 |
| 4 | `apify~cheerio-scraper` | Web (static HTML) | 6.2 |
| 5 | `trudax~reddit-scraper-lite` | Reddit | 6.8 |
| 6 | `apidojo~tweet-scraper` | Twitter / X | 6.5 |
| 7 | `apify~instagram-scraper` | Instagram | 6.6 |
| 8 | `streamers~youtube-scraper` | YouTube | 6.9 |
| 9 | `clockworks~tiktok-scraper` | TikTok | 6.10 |
| 10 | `apimaestro~linkedin-profile-batch-scraper-no-cookies-required` | LinkedIn Profiles | 6.4 |
| 11 | `harvestapi~linkedin-profile-search` | LinkedIn Profile Search | 6.4 |
| 12 | `harvestapi~linkedin-company-employees` | LinkedIn Employees | 6.4 |
| 13 | `apimaestro~linkedin-posts-search-scraper-no-cookies` | LinkedIn Posts | 6.4 |
| 14 | `junglee~amazon-crawler` | Amazon | 6.7 |
| 15 | `compass~crawler-google-places` | Google Maps / Places | 6.11 |

All IDs sourced from technical reference Section 6 only. To add a new actor: update `ACTOR_REGISTRY` in `actor_registry.py`, add a mock fixture in `apify_client.py`, and update this table.

---

## Flagged Uncertainties (Verify Sunday Before Live Mode)

| # | Actor | Field | Status | Verification Command |
|---|---|---|---|---|
| 1 | `apimaestro~linkedin-profile-batch-scraper-no-cookies-required` | `urls` (input list of profile URLs) | Using as confirmed by user; verify live | `GET /v2/acts/apimaestro~linkedin-profile-batch-scraper-no-cookies-required/builds/default` |
| 2 | `harvestapi~linkedin-company-employees` | `companyUrls` (input list of company names/URLs) | Using as confirmed by user; verify live | `GET /v2/acts/harvestapi~linkedin-company-employees/builds/default` |
| 3 | `harvestapi~linkedin-company-employees` | `mode` field name (value: `"Short"`) | Inferred from reference Section 6.4; verify live | Same as above |
| 4 | `trudax~reddit-scraper-lite` | `searches` field type (string array vs object array) | Using plain string array per reference Section 6.8; verify live | `GET /v2/acts/trudax~reddit-scraper-lite/builds/default` |
| 5 | `compass~crawler-google-places` | `scrapeSocialMediaProfiles` shape | Omitting entirely unless required | `GET /v2/acts/compass~crawler-google-places/builds/default` |

---

## How to Resume This Session

### If continuing from scratch in a new Claude session:

1. Read this file (`CLAUDE.md`) for full context
2. Check the **Build Status** section — find the first unchecked box
3. Read the plan file at:
   `~/.claude/plans/i-m-building-an-ai-iterative-dongarra.md`
   for the detailed function signatures of the next file to build
4. Build that file, run `python -m py_compile backend/<file>.py`, confirm no errors
5. Check the box in this file, then stop and wait for user confirmation

### To run the server (after all files are built):
```bash
cd /Users/ethanngo/Desktop/apify-orchestrator
pip install -r requirements.txt
uvicorn backend.main:app --reload
# Then open frontend/index.html in a browser (or serve it)
```

### To verify mock mode works:
```bash
curl -s http://localhost:8000/health | python -m json.tool
curl -s -X POST http://localhost:8000/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"user_query": "What are people saying about OpenAI on Reddit and Twitter this week?"}' \
  | python -m json.tool
```

### To switch to live mode (Sunday):
1. Edit `.env`: set `MOCK_MODE=false`
2. Add your real `APIFY_TOKEN` and `ANTHROPIC_API_KEY`
3. Verify the 5 flagged field names in the table above before running Query 1 or 3
4. Run Query 2 first (cheapest: Reddit + Twitter, ~100 items total)

---

## Apify API Quick Reference

- **Base URL:** `https://api.apify.com/v2`
- **Auth header:** `Authorization: Bearer <APIFY_TOKEN>`
- **Start actor:** `POST /v2/acts/{actorId}/runs` (body = run_input JSON)
- **Poll run:** `GET /v2/actor-runs/{runId}` until status in `{SUCCEEDED, FAILED, TIMED-OUT, ABORTED}`
- **Get results:** `GET /v2/datasets/{datasetId}/items?format=json&clean=true&limit=100`
  - NOTE: returns raw JSON array, NOT wrapped in `{"data": [...]}`
- **Actor ID format:** `username~actor-name` (e.g. `apify~google-search-scraper`)
- **Python client:** `apify_client.ApifyClient(token).actor(id).call(run_input=...)` handles polling automatically
