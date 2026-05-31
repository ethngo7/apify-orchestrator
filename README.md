# Apify Actor Orchestrator

## 🚀 Live Demo

**[https://apify-orchestrator.up.railway.app](https://apify-orchestrator.up.railway.app)**

> Running in MOCK MODE — no Apify credits consumed. Try the 3 demo queries below.

---

## Try These Demo Queries

Paste any of these into the input box and click **Run Agent**:

1. **AI Startups SF**
   > "Find me the top AI startups in SF, their founders' LinkedIn profiles, and what people are saying about them on Reddit"

2. **OpenAI Sentiment**
   > "What are people saying about OpenAI on Reddit and Twitter this week?"

3. **Fintech Lead Gen NYC**
   > "Build me a lead list of fintech companies in NYC — find them on Google Maps, then find their decision makers on LinkedIn"

---

An AI agent that accepts natural language queries, searches Apify's marketplace of 33,000+ Actors, selects the right Actor(s), chains them when needed, executes them, and returns structured data with a synthesized prose summary.

Runs in **MOCK MODE** by default — no Apify credits consumed during development.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment (edit .env — add your real keys for live mode)
cp .env .env.local   # optional: keep a local override

# 3. Start the server
uvicorn backend.main:app --reload

# 4. Open the frontend
open frontend/index.html   # or just double-click it in Finder
```

The frontend calls `http://localhost:8000` — make sure the server is running before opening it.

---

## Verify Mock Mode

```bash
# Health check
curl -s http://localhost:8000/health | python -m json.tool

# Run a demo query
curl -s -X POST http://localhost:8000/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"user_query": "What are people saying about OpenAI on Reddit and Twitter this week?"}' \
  | python -m json.tool
```

Expected health response:
```json
{"status": "ok", "mock_mode": true, "version": "1.0.0"}
```

---

## Demo Queries

### Query 1 — AI Startups SF
> "Find me the top AI startups in SF, their founders' LinkedIn profiles, and what people are saying about them on Reddit"

Chain: Google Search → LinkedIn Profile Scraper → Reddit Scraper (5 iterations)

### Query 2 — OpenAI Sentiment
> "What are people saying about OpenAI on Reddit and Twitter this week?"

Chain: Reddit Scraper → Tweet Scraper (4 iterations)

### Query 3 — Fintech Lead Gen NYC
> "Build me a lead list of fintech companies in NYC — find them on Google Maps, then find their decision makers on LinkedIn"

Chain: Google Maps/Places → LinkedIn Company Employees (4 iterations)

---

## Sunday Live Mode Checklist

1. Edit `.env`:
   ```
   MOCK_MODE=false
   APIFY_TOKEN=<your real token>
   ANTHROPIC_API_KEY=<your real key>
   ```

2. Verify the 5 flagged actor input fields (see `CLAUDE.md` → Flagged Uncertainties):
   - `urls` — `apimaestro~linkedin-profile-batch-scraper-no-cookies-required`
   - `companyUrls` + `mode` — `harvestapi~linkedin-company-employees`
   - `searches` field type — `trudax~reddit-scraper-lite`
   - `scrapeSocialMediaProfiles` shape — `compass~crawler-google-places`

3. Run Query 2 first (cheapest: Reddit + Twitter, ~100 items total).

4. Run Query 3, then Query 1.

---

## Architecture

```
POST /orchestrate
  └── parse_query()        → ParsedIntent           (Claude call 1)
  └── plan_execution()     → ExecutionPlan           (Tier 1: registry lookup, no Claude call)
                                                     (Tier 2: Claude call 2 if no registry match)
  └── execute_plan()       → list[AgentStep]         (one Apify run per step)
        └── Tier 2 only:  discover_actor_from_store() (2 extra Claude calls + 1 store search)
  └── synthesize_results() → str                     (final Claude call)
```

**Two-tier actor selection:**
- **Tier 1** — 15 hardcoded actors in `ACTOR_REGISTRY` (fast path, no extra API calls)
- **Tier 2** — 33,000+ actors via live Apify Store search (triggered when registry has no match)

**Budget:** `MAX_ITERATIONS=5`, `MAX_TOKENS_PER_RUN=10,000`

---

## File Structure

```
/apify-orchestrator
  .env                       ← MOCK_MODE, APIFY_TOKEN, ANTHROPIC_API_KEY
  requirements.txt
  README.md
  CLAUDE.md                  ← living build reference (update after each file)
  /backend
    models.py                ← Pydantic v2 models
    apify_client.py          ← Apify REST wrapper + mock fixtures
    actor_registry.py        ← 15 curated actors, demo classifier, input builder
    agent.py                 ← ReAct agentic loop
    main.py                  ← FastAPI app (/health, /orchestrate)
  /frontend
    index.html               ← Single-file React + Tailwind UI (no build step)
```
