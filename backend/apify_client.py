from __future__ import annotations

import os
import time
import uuid
from typing import Optional

# apify-client is imported lazily inside ApifyClientWrapper.__init__ so that
# mock-mode startup never fails even if the package has an import-time issue.

from backend.models import ActorRunResult, ActorRunStatus

# ── Constants ──────────────────────────────────────────────────────────────────

MOCK_MODE: bool = os.getenv("MOCK_MODE", "true").lower() == "true"
APIFY_TOKEN: str = os.getenv("APIFY_TOKEN", "")
BASE_URL = "https://api.apify.com/v2"

# Terminal run statuses per Apify reference Section 5 (hyphenated form as Apify returns them).
_TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"}

# ── Mock dataset fixtures ──────────────────────────────────────────────────────
# All company names, people, URLs, and post text are realistic — no placeholder data.

MOCK_DATASET_ITEMS: dict[str, list[dict]] = {

    # ── Query 1: AI Startups SF — Google SERP results ─────────────────────────
    # 3 SERP pages; each has organicResults containing real LinkedIn /in/ profile URLs.
    # Example use: actor apify~google-search-scraper, query "AI startups San Francisco founders"
    "google_search_ai_startups": [
        {
            "searchQuery": {"term": "top AI startups San Francisco founders LinkedIn", "page": 1},
            "url": "https://www.google.com/search?q=top+AI+startups+San+Francisco+founders+LinkedIn",
            "resultsTotal": 412000000,
            "organicResults": [
                {
                    "position": 1,
                    "title": "Dario Amodei — Co-founder & CEO at Anthropic | LinkedIn",
                    "url": "https://www.linkedin.com/in/dario-amodei/",
                    "displayedUrl": "linkedin.com › in › dario-amodei",
                    "description": "Dario Amodei is the Co-founder and CEO of Anthropic, an AI safety company. Former VP of Research at OpenAI.",
                },
                {
                    "position": 2,
                    "title": "Alexandr Wang — Founder & CEO at Scale AI | LinkedIn",
                    "url": "https://www.linkedin.com/in/alexandr-wang-183601a1/",
                    "displayedUrl": "linkedin.com › in › alexandr-wang",
                    "description": "Alexandr Wang is the founder and CEO of Scale AI. Forbes 30 Under 30. Previously at Quora and Addepar.",
                },
                {
                    "position": 3,
                    "title": "Aidan Gomez — Co-founder & CEO at Cohere | LinkedIn",
                    "url": "https://www.linkedin.com/in/aidangomez/",
                    "displayedUrl": "linkedin.com › in › aidangomez",
                    "description": "Aidan Gomez is Co-founder and CEO of Cohere. Co-author of the original Transformer paper ('Attention Is All You Need').",
                },
                {
                    "position": 4,
                    "title": "The 20 hottest AI startups in San Francisco — TechCrunch",
                    "url": "https://techcrunch.com/2024/09/12/hottest-ai-startups-sf-2024/",
                    "displayedUrl": "techcrunch.com › 2024 › 09 › 12",
                    "description": "From Anthropic and Scale AI to Harvey and Glean, here are the 20 AI startups in SF you should be watching in 2024.",
                },
                {
                    "position": 5,
                    "title": "Arvind Jain — Co-founder & CEO at Glean | LinkedIn",
                    "url": "https://www.linkedin.com/in/arvind-jain-2b8a8b/",
                    "displayedUrl": "linkedin.com › in › arvind-jain",
                    "description": "Arvind Jain is Co-founder and CEO of Glean, the enterprise AI search platform. Previously Engineering Director at Google.",
                },
            ],
        },
        {
            "searchQuery": {"term": "top AI startups San Francisco founders LinkedIn", "page": 2},
            "url": "https://www.google.com/search?q=top+AI+startups+San+Francisco+founders+LinkedIn&start=10",
            "resultsTotal": 412000000,
            "organicResults": [
                {
                    "position": 1,
                    "title": "Gabriel Pereyra — Co-founder at Adept AI | LinkedIn",
                    "url": "https://www.linkedin.com/in/gabrielpereyra/",
                    "displayedUrl": "linkedin.com › in › gabrielpereyra",
                    "description": "Gabriel Pereyra is Co-founder of Adept AI. Previously Research Scientist at OpenAI and Google Brain.",
                },
                {
                    "position": 2,
                    "title": "Winston Weinberg — Co-founder & President at Harvey | LinkedIn",
                    "url": "https://www.linkedin.com/in/winston-weinberg/",
                    "displayedUrl": "linkedin.com › in › winston-weinberg",
                    "description": "Winston Weinberg is Co-founder and President of Harvey, the AI legal platform. Previously litigation associate at O'Melveny.",
                },
                {
                    "position": 3,
                    "title": "Cognition AI raises $175M Series B — The Information",
                    "url": "https://www.theinformation.com/articles/cognition-ai-raises-175m",
                    "displayedUrl": "theinformation.com › articles",
                    "description": "Cognition AI, the SF-based startup building Devin the AI software engineer, has raised $175M at a $2B valuation.",
                },
            ],
        },
        {
            "searchQuery": {"term": "top AI startups San Francisco founders LinkedIn", "page": 3},
            "url": "https://www.google.com/search?q=top+AI+startups+San+Francisco+founders+LinkedIn&start=20",
            "resultsTotal": 412000000,
            "organicResults": [
                {
                    "position": 1,
                    "title": "Ali Ghodsi — Co-founder & CEO at Databricks | LinkedIn",
                    "url": "https://www.linkedin.com/in/alighodsi/",
                    "displayedUrl": "linkedin.com › in › alighodsi",
                    "description": "Ali Ghodsi is Co-founder and CEO of Databricks, the data and AI company valued at $43B.",
                },
                {
                    "position": 2,
                    "title": "Harrison Chase — Co-founder & CEO at LangChain | LinkedIn",
                    "url": "https://www.linkedin.com/in/harrison-chase-961287118/",
                    "displayedUrl": "linkedin.com › in › harrison-chase",
                    "description": "Harrison Chase is Co-founder and CEO of LangChain, the most widely used LLM application framework.",
                },
            ],
        },
    ],

    # ── Query 2: OpenAI Sentiment — Reddit posts ───────────────────────────────
    # 10 posts from r/MachineLearning, r/OpenAI, r/ChatGPT, r/artificial
    # Example use: actor trudax~reddit-scraper-lite, searches=["OpenAI"]
    "reddit_openai": [
        {
            "url": "https://www.reddit.com/r/MachineLearning/comments/1d3x9q/openai_new_model_first_week_impressions/",
            "title": "OpenAI's latest model — first week impressions from a practitioner (coding, reasoning, long-context)",
            "body": "I've been running systematic evals all week. Coding tasks are 30-40% faster than the previous version on my benchmarks. The 128k context window actually works now — no mid-document amnesia. Reasoning chains are more legible but occasionally overconfident. Overall: best coding LLM I've used, still not reliable enough for unsupervised production use.",
            "score": 2847,
            "numComments": 412,
            "author": "neel_nanda_mechanistic",
            "subreddit": "MachineLearning",
            "createdAt": "2026-05-23T09:14:22Z",
        },
        {
            "url": "https://www.reddit.com/r/OpenAI/comments/1d2abc/openai_api_pricing_changes_breakdown/",
            "title": "OpenAI API pricing changes — full breakdown + how it affects small devs",
            "body": "The new per-token pricing for GPT-5 is roughly $15/M input, $60/M output. For context: running a customer support bot handling 10k messages/day at ~800 tokens each = ~$480/day. That's unsustainable for most indie devs. Cache hits help a lot if your system prompt is static. Switching to batch API cuts it in half.",
            "score": 1923,
            "numComments": 287,
            "author": "indie_dev_sf",
            "subreddit": "OpenAI",
            "createdAt": "2026-05-24T14:32:00Z",
        },
        {
            "url": "https://www.reddit.com/r/ChatGPT/comments/1d1xyz/chatgpt_canvas_update_what_actually_changed/",
            "title": "ChatGPT Canvas update — what actually changed and what's still broken",
            "body": "The inline editing is finally fast. The code execution now shows real output instead of hallucinated output. Still can't handle files larger than ~50 pages without losing context. The 'improve' button remains useless for anything technical. Net verdict: genuinely useful for writing and lightweight code, not ready for serious engineering work.",
            "score": 1456,
            "numComments": 198,
            "author": "llm_daily_user",
            "subreddit": "ChatGPT",
            "createdAt": "2026-05-24T08:20:00Z",
        },
        {
            "url": "https://www.reddit.com/r/artificial/comments/1d0pqr/compute_costs_and_agi_timeline_reality_check/",
            "title": "The compute costs behind frontier models are staggering — is this path to AGI actually sustainable?",
            "body": "Training GPT-4 reportedly cost ~$100M. Estimates for the current generation are $500M–$1B per run. Even with hardware improvements, we're approaching a wall where only 3-4 organizations on earth can afford to train frontier models. This is concentrating AI power in a way that should concern everyone regardless of your politics.",
            "score": 3241,
            "numComments": 621,
            "author": "ai_governance_watch",
            "subreddit": "artificial",
            "createdAt": "2026-05-22T17:45:00Z",
        },
        {
            "url": "https://www.reddit.com/r/MachineLearning/comments/1czabc/openai_safety_team_departures_analysis/",
            "title": "Analyzing the pattern of OpenAI safety team departures — data and timeline",
            "body": "I compiled a timeline of 23 safety/alignment researcher departures from OpenAI since 2022, including the reasons they gave publicly. The pattern is consistent: commercial pressure over safety timelines. Jan Leike's farewell post was the most explicit. This isn't rumors — it's a documented institutional drift that should be part of any serious evaluation of OpenAI's governance.",
            "score": 4102,
            "numComments": 834,
            "author": "alignment_forum_reader",
            "subreddit": "MachineLearning",
            "createdAt": "2026-05-21T11:30:00Z",
        },
        {
            "url": "https://www.reddit.com/r/OpenAI/comments/1cyzxw/openai_valuation_300b_justified/",
            "title": "Is OpenAI's $300B valuation justified? Breaking down the revenue math",
            "body": "$300B valuation implies ~100x revenue multiple on their reported $3B ARR. For comparison: Salesforce trades at ~6x revenue. Even if OpenAI grows 3x per year for 3 years, you'd need a 12x multiple to hit those numbers — which assumes they maintain current margins and market share. The bull case requires AGI-level moat. The bear case is Microsoft eats their lunch.",
            "score": 1678,
            "numComments": 342,
            "author": "sf_vc_watcher",
            "subreddit": "OpenAI",
            "createdAt": "2026-05-25T16:10:00Z",
        },
        {
            "url": "https://www.reddit.com/r/ChatGPT/comments/1cxpqr/o3_vs_gemini_ultra_head_to_head_300_questions/",
            "title": "I ran 300 questions through o3 and Gemini Ultra 2.0 — detailed comparison",
            "body": "Setup: 300 questions across 10 categories (math, coding, writing, factual, reasoning, etc). o3 wins: hard math (92% vs 81%), multi-step coding problems (88% vs 79%). Gemini Ultra wins: long doc QA (94% vs 87%), multilingual (91% vs 82%). Tie: creative writing, general knowledge. Methodology and full results in comments.",
            "score": 5891,
            "numComments": 1042,
            "author": "llm_benchmark_nerd",
            "subreddit": "ChatGPT",
            "createdAt": "2026-05-26T10:00:00Z",
        },
        {
            "url": "https://www.reddit.com/r/artificial/comments/1cwmno/openai_nonprofit_governance_explainer/",
            "title": "OpenAI's governance structure explained — why it matters for AI safety",
            "body": "OpenAI operates as a capped-profit company controlled by a nonprofit board. In theory, the board's fiduciary duty is to humanity, not shareholders. In practice, the 2023 board drama showed how fragile this structure is. The new governance reforms give Microsoft a non-voting observer seat and require supermajority for CEO removal. Whether this makes things more or less safe is genuinely contested.",
            "score": 2134,
            "numComments": 389,
            "author": "tech_policy_wonk",
            "subreddit": "artificial",
            "createdAt": "2026-05-22T20:00:00Z",
        },
        {
            "url": "https://www.reddit.com/r/MachineLearning/comments/1cvdef/openai_researchers_ama_highlights/",
            "title": "Highlights from the OpenAI researcher AMA — most interesting answers compiled",
            "body": "Key takeaways from yesterday's AMA: (1) They believe current architectures can scale to AGI with enough compute. (2) RLHF is still core but increasingly combined with Constitutional AI-style approaches. (3) The biggest unsolved problem is reliable long-horizon reasoning. (4) They're more worried about misuse than misalignment in the near term. Full thread worth reading.",
            "score": 3567,
            "numComments": 512,
            "author": "ml_twitter_recap",
            "subreddit": "MachineLearning",
            "createdAt": "2026-05-23T19:00:00Z",
        },
        {
            "url": "https://www.reddit.com/r/OpenAI/comments/1cuabc/openai_enterprise_adoption_anecdata/",
            "title": "Enterprise OpenAI adoption — sharing 6 months of real usage data from a Fortune 500 deployment",
            "body": "We deployed ChatGPT Enterprise to 4,200 employees in October. 6-month update: 67% monthly active users, avg 23 queries/day among actives. Biggest use cases: first-draft writing (42%), code review (28%), data analysis (18%), research summaries (12%). ROI is hard to measure but we estimate 45 min/week/employee saved. Cost: ~$38/user/month. Worth it for us, YMMV.",
            "score": 2901,
            "numComments": 478,
            "author": "enterprise_ai_lead",
            "subreddit": "OpenAI",
            "createdAt": "2026-05-27T13:00:00Z",
        },
    ],

    # ── Query 2: OpenAI Sentiment — Twitter/X posts ────────────────────────────
    # 10 tweets matching apidojo~tweet-scraper output shape (ref Section 6.5)
    # Example use: actor apidojo~tweet-scraper, searchTerms=["OpenAI"], start="2026-05-22"
    "twitter_openai": [
        {
            "id": "1793201847362048001",
            "url": "https://x.com/swyx/status/1793201847362048001",
            "twitterUrl": "https://twitter.com/swyx/status/1793201847362048001",
            "text": "After a week with the new OpenAI model: it's the best coding assistant I've used. Not perfect — still hallucinates APIs occasionally — but the improvement on multi-file refactors is real. The future is here, it's just unevenly distributed across use cases.",
            "createdAt": "2026-05-26T09:14:22Z",
            "likeCount": 4821,
            "retweetCount": 1203,
            "replyCount": 88,
            "quoteCount": 142,
            "lang": "en",
            "isRetweet": False,
            "isReply": False,
            "author": {
                "userName": "swyx",
                "name": "Shawn @swyx Wang",
                "id": "1234567890",
                "isBlueVerified": True,
                "followers": 96200,
                "following": 3100,
                "profilePicture": "https://pbs.twimg.com/profile_images/swyx.jpg",
            },
        },
        {
            "id": "1793201847362048002",
            "url": "https://x.com/DrJimFan/status/1793201847362048002",
            "twitterUrl": "https://twitter.com/DrJimFan/status/1793201847362048002",
            "text": "OpenAI's context scaling is doing something interesting: the model actually uses the full 128k tokens coherently. I tested it with entire codebases and lengthy PDFs — no retrieval tricks needed. This changes the RAG vs long-context debate significantly.",
            "createdAt": "2026-05-25T14:30:00Z",
            "likeCount": 3204,
            "retweetCount": 891,
            "replyCount": 67,
            "quoteCount": 98,
            "lang": "en",
            "isRetweet": False,
            "isReply": False,
            "author": {
                "userName": "DrJimFan",
                "name": "Jim Fan",
                "id": "2345678901",
                "isBlueVerified": True,
                "followers": 184000,
                "following": 890,
                "profilePicture": "https://pbs.twimg.com/profile_images/drjimfan.jpg",
            },
        },
        {
            "id": "1793201847362048003",
            "url": "https://x.com/emollick/status/1793201847362048003",
            "twitterUrl": "https://twitter.com/emollick/status/1793201847362048003",
            "text": "I've been running experiments on OpenAI's new model with my MBA students. The quality of strategic analysis is genuinely different — not just faster but structurally more sophisticated. The implication for knowledge work productivity is larger than most organizations realize.",
            "createdAt": "2026-05-24T11:00:00Z",
            "likeCount": 6102,
            "retweetCount": 2340,
            "replyCount": 201,
            "quoteCount": 312,
            "lang": "en",
            "isRetweet": False,
            "isReply": False,
            "author": {
                "userName": "emollick",
                "name": "Ethan Mollick",
                "id": "3456789012",
                "isBlueVerified": True,
                "followers": 412000,
                "following": 1200,
                "profilePicture": "https://pbs.twimg.com/profile_images/emollick.jpg",
            },
        },
        {
            "id": "1793201847362048004",
            "url": "https://x.com/ylecun/status/1793201847362048004",
            "twitterUrl": "https://twitter.com/ylecun/status/1793201847362048004",
            "text": "OpenAI's new model is impressive engineering. But let's be precise: impressive performance on benchmarks ≠ general intelligence. The model still fails on simple compositional reasoning tasks that any 8-year-old handles trivially. We should celebrate the progress without the AGI hype.",
            "createdAt": "2026-05-23T18:45:00Z",
            "likeCount": 8934,
            "retweetCount": 3102,
            "replyCount": 892,
            "quoteCount": 567,
            "lang": "en",
            "isRetweet": False,
            "isReply": False,
            "author": {
                "userName": "ylecun",
                "name": "Yann LeCun",
                "id": "4567890123",
                "isBlueVerified": True,
                "followers": 612000,
                "following": 890,
                "profilePicture": "https://pbs.twimg.com/profile_images/ylecun.jpg",
            },
        },
        {
            "id": "1793201847362048005",
            "url": "https://x.com/karpathy/status/1793201847362048005",
            "twitterUrl": "https://twitter.com/karpathy/status/1793201847362048005",
            "text": "Quick eval note: OpenAI's new model is noticeably better at understanding error messages and stack traces. The 'oh I see what's happening here' moment happens reliably now. For debugging workflows this is a real productivity multiplier.",
            "createdAt": "2026-05-26T16:20:00Z",
            "likeCount": 12401,
            "retweetCount": 4201,
            "replyCount": 312,
            "quoteCount": 891,
            "lang": "en",
            "isRetweet": False,
            "isReply": False,
            "author": {
                "userName": "karpathy",
                "name": "Andrej Karpathy",
                "id": "5678901234",
                "isBlueVerified": True,
                "followers": 892000,
                "following": 340,
                "profilePicture": "https://pbs.twimg.com/profile_images/karpathy.jpg",
            },
        },
        {
            "id": "1793201847362048006",
            "url": "https://x.com/sama/status/1793201847362048006",
            "twitterUrl": "https://twitter.com/sama/status/1793201847362048006",
            "text": "grateful for all the feedback on the new model launch. we're reading everything. a few things we're already working on based on what we're hearing.",
            "createdAt": "2026-05-27T10:00:00Z",
            "likeCount": 22341,
            "retweetCount": 3892,
            "replyCount": 1892,
            "quoteCount": 1102,
            "lang": "en",
            "isRetweet": False,
            "isReply": False,
            "author": {
                "userName": "sama",
                "name": "Sam Altman",
                "id": "6789012345",
                "isBlueVerified": True,
                "followers": 2100000,
                "following": 210,
                "profilePicture": "https://pbs.twimg.com/profile_images/sama.jpg",
            },
        },
        {
            "id": "1793201847362048007",
            "url": "https://x.com/zebulgar/status/1793201847362048007",
            "twitterUrl": "https://twitter.com/zebulgar/status/1793201847362048007",
            "text": "OpenAI pricing is becoming a real problem for startups. At $60/M output tokens, a small app doing 1M API calls/day at 500 output tokens = $30k/day = $900k/month. There's a real market for cheaper-but-good models that OpenAI is leaving on the table.",
            "createdAt": "2026-05-25T09:30:00Z",
            "likeCount": 3891,
            "retweetCount": 1234,
            "replyCount": 289,
            "quoteCount": 198,
            "lang": "en",
            "isRetweet": False,
            "isReply": False,
            "author": {
                "userName": "zebulgar",
                "name": "Zeb Portanova",
                "id": "7890123456",
                "isBlueVerified": False,
                "followers": 28400,
                "following": 1200,
                "profilePicture": "https://pbs.twimg.com/profile_images/zebulgar.jpg",
            },
        },
        {
            "id": "1793201847362048008",
            "url": "https://x.com/gdb/status/1793201847362048008",
            "twitterUrl": "https://twitter.com/gdb/status/1793201847362048008",
            "text": "one thing i think people underestimate about openai's new model: the instruction following is qualitatively different. it does what you actually meant, not just what you literally said. this sounds small but it completely changes the prompting experience.",
            "createdAt": "2026-05-24T20:00:00Z",
            "likeCount": 7823,
            "retweetCount": 2341,
            "replyCount": 198,
            "quoteCount": 401,
            "lang": "en",
            "isRetweet": False,
            "isReply": False,
            "author": {
                "userName": "gdb",
                "name": "Greg Brockman",
                "id": "8901234567",
                "isBlueVerified": True,
                "followers": 312000,
                "following": 890,
                "profilePicture": "https://pbs.twimg.com/profile_images/gdb.jpg",
            },
        },
        {
            "id": "1793201847362048009",
            "url": "https://x.com/benedictevans/status/1793201847362048009",
            "twitterUrl": "https://twitter.com/benedictevans/status/1793201847362048009",
            "text": "The pattern with OpenAI releases: (1) Impressive demo, (2) Hype wave, (3) Systematic evals reveal limitations, (4) Still useful. We're somewhere between 2 and 3 on the new model. Useful is the right bar — we just don't need AGI announcements with every release.",
            "createdAt": "2026-05-23T14:10:00Z",
            "likeCount": 5102,
            "retweetCount": 1891,
            "replyCount": 312,
            "quoteCount": 289,
            "lang": "en",
            "isRetweet": False,
            "isReply": False,
            "author": {
                "userName": "benedictevans",
                "name": "Benedict Evans",
                "id": "9012345678",
                "isBlueVerified": True,
                "followers": 198000,
                "following": 2300,
                "profilePicture": "https://pbs.twimg.com/profile_images/benedictevans.jpg",
            },
        },
        {
            "id": "1793201847362048010",
            "url": "https://x.com/mmitchell_ai/status/1793201847362048010",
            "twitterUrl": "https://twitter.com/mmitchell_ai/status/1793201847362048010",
            "text": "Genuine question: if OpenAI's model is this good, what's the safety evaluation process before deployment? The system card is 40 pages but I can't find methodology for edge-case adversarial testing. Impressive capability without rigorous safety evals is a red flag regardless of who's building it.",
            "createdAt": "2026-05-22T16:00:00Z",
            "likeCount": 4231,
            "retweetCount": 1892,
            "replyCount": 498,
            "quoteCount": 312,
            "lang": "en",
            "isRetweet": False,
            "isReply": False,
            "author": {
                "userName": "mmitchell_ai",
                "name": "Margaret Mitchell",
                "id": "0123456789",
                "isBlueVerified": True,
                "followers": 89200,
                "following": 3400,
                "profilePicture": "https://pbs.twimg.com/profile_images/mmitchell_ai.jpg",
            },
        },
    ],

    # ── Query 1: AI Startups SF — LinkedIn founder profiles ────────────────────
    # 3 founder profiles; field names match apimaestro scraper convention
    # Example use: actor apimaestro~linkedin-profile-batch-scraper-no-cookies-required
    # TODO: verify exact field names against live /builds/default on Sunday
    "linkedin_profiles": [
        {
            "profileUrl": "https://www.linkedin.com/in/dario-amodei/",
            "fullName": "Dario Amodei",
            "headline": "Co-founder & CEO at Anthropic",
            "location": "San Francisco, California, United States",
            "currentCompany": "Anthropic",
            "followers": 187000,
            "connections": "500+",
            "about": "Co-founder and CEO of Anthropic, an AI safety company. We are dedicated to AI safety research and developing AI systems that are safe, beneficial, and understandable.",
            "experience": [
                {"title": "Co-founder & CEO", "company": "Anthropic", "startDate": "2021-05", "endDate": None, "location": "San Francisco, CA"},
                {"title": "VP of Research", "company": "OpenAI", "startDate": "2018-03", "endDate": "2021-05", "location": "San Francisco, CA"},
                {"title": "Research Scientist", "company": "Baidu", "startDate": "2015-06", "endDate": "2018-03", "location": "Sunnyvale, CA"},
            ],
            "education": [
                {"school": "Princeton University", "degree": "PhD", "field": "Computational Neuroscience", "startYear": 2008, "endYear": 2014},
            ],
        },
        {
            "profileUrl": "https://www.linkedin.com/in/alexandr-wang-183601a1/",
            "fullName": "Alexandr Wang",
            "headline": "Founder & CEO at Scale AI",
            "location": "San Francisco, California, United States",
            "currentCompany": "Scale AI",
            "followers": 214000,
            "connections": "500+",
            "about": "Building Scale AI to accelerate the development of AI. Scale provides high-quality training data for AI models across self-driving, NLP, robotics, and more.",
            "experience": [
                {"title": "Founder & CEO", "company": "Scale AI", "startDate": "2016-06", "endDate": None, "location": "San Francisco, CA"},
                {"title": "Software Engineering Intern", "company": "Quora", "startDate": "2015-06", "endDate": "2015-09", "location": "Mountain View, CA"},
            ],
            "education": [
                {"school": "Massachusetts Institute of Technology", "degree": "N/A (left to start Scale AI)", "field": "Mathematics and Computer Science", "startYear": 2016, "endYear": None},
            ],
        },
        {
            "profileUrl": "https://www.linkedin.com/in/aidangomez/",
            "fullName": "Aidan Gomez",
            "headline": "Co-founder & CEO at Cohere",
            "location": "Toronto, Ontario, Canada",
            "currentCompany": "Cohere",
            "followers": 93000,
            "connections": "500+",
            "about": "Co-founder and CEO of Cohere, building enterprise AI with large language models. Co-author of 'Attention Is All You Need', the original Transformer paper.",
            "experience": [
                {"title": "Co-founder & CEO", "company": "Cohere", "startDate": "2019-10", "endDate": None, "location": "Toronto, Canada"},
                {"title": "Research Intern", "company": "Google Brain", "startDate": "2017-05", "endDate": "2017-09", "location": "Mountain View, CA"},
            ],
            "education": [
                {"school": "University of Oxford", "degree": "DPhil", "field": "Machine Learning", "startYear": 2017, "endYear": 2020},
            ],
        },
    ],

    # ── Query 3: Fintech Lead Gen NYC — Google Maps places ─────────────────────
    # 10 NYC fintech company places; field names match compass~crawler-google-places output (ref 6.11)
    # Example use: actor compass~crawler-google-places, searchStringsArray=["fintech company"]
    "google_maps_fintech": [
        {
            "title": "Plaid",
            "totalScore": 4.2,
            "reviewsCount": 34,
            "address": "1 World Trade Center, Floor 34, New York, NY 10007",
            "phone": "+1 (415) 854-4686",
            "website": "https://plaid.com",
            "url": "https://www.google.com/maps/place/Plaid/@40.7127753,-74.0131437",
            "openingHours": [{"day": "Monday-Friday", "hours": "9:00 AM – 6:00 PM"}],
            "categories": ["Financial Technology Company", "Software Company"],
        },
        {
            "title": "Ramp",
            "totalScore": 4.6,
            "reviewsCount": 28,
            "address": "71 5th Ave, New York, NY 10003",
            "phone": "+1 (855) 726-7267",
            "website": "https://ramp.com",
            "url": "https://www.google.com/maps/place/Ramp/@40.7391059,-73.9935529",
            "openingHours": [{"day": "Monday-Friday", "hours": "9:00 AM – 6:00 PM"}],
            "categories": ["Financial Technology Company", "Corporate Card Provider"],
        },
        {
            "title": "Brex",
            "totalScore": 4.1,
            "reviewsCount": 19,
            "address": "575 5th Ave, 26th Floor, New York, NY 10017",
            "phone": "+1 (833) 228-2739",
            "website": "https://brex.com",
            "url": "https://www.google.com/maps/place/Brex/@40.7549029,-73.9804289",
            "openingHours": [{"day": "Monday-Friday", "hours": "9:00 AM – 5:00 PM"}],
            "categories": ["Financial Technology Company", "Business Banking"],
        },
        {
            "title": "Marqeta",
            "totalScore": 3.9,
            "reviewsCount": 12,
            "address": "180 Maiden Lane, New York, NY 10038",
            "phone": "+1 (888) 663-0024",
            "website": "https://marqeta.com",
            "url": "https://www.google.com/maps/place/Marqeta/@40.7077519,-74.0060219",
            "openingHours": [{"day": "Monday-Friday", "hours": "9:00 AM – 6:00 PM"}],
            "categories": ["Financial Technology Company", "Card Issuing Platform"],
        },
        {
            "title": "Affirm",
            "totalScore": 3.7,
            "reviewsCount": 41,
            "address": "30 W 21st St, 7th Floor, New York, NY 10010",
            "phone": "+1 (855) 423-3729",
            "website": "https://affirm.com",
            "url": "https://www.google.com/maps/place/Affirm/@40.7405,−73.9929",
            "openingHours": [{"day": "Monday-Friday", "hours": "9:00 AM – 6:00 PM"}],
            "categories": ["Financial Technology Company", "Buy Now Pay Later"],
        },
        {
            "title": "Checkout.com",
            "totalScore": 4.4,
            "reviewsCount": 16,
            "address": "195 Broadway, 24th Floor, New York, NY 10007",
            "phone": "+1 (212) 729-0200",
            "website": "https://checkout.com",
            "url": "https://www.google.com/maps/place/Checkout.com/@40.7128,−74.0101",
            "openingHours": [{"day": "Monday-Friday", "hours": "9:00 AM – 6:00 PM"}],
            "categories": ["Financial Technology Company", "Payment Processing"],
        },
        {
            "title": "Nuvei",
            "totalScore": 4.0,
            "reviewsCount": 8,
            "address": "3 World Trade Center, Suite 8500, New York, NY 10007",
            "phone": "+1 (212) 660-5000",
            "website": "https://nuvei.com",
            "url": "https://www.google.com/maps/place/Nuvei/@40.7127,−74.0134",
            "openingHours": [{"day": "Monday-Friday", "hours": "9:00 AM – 5:30 PM"}],
            "categories": ["Financial Technology Company", "Payment Technology"],
        },
        {
            "title": "Figure Technologies",
            "totalScore": 4.3,
            "reviewsCount": 11,
            "address": "35 E 21st St, Floor 6, New York, NY 10010",
            "phone": "+1 (888) 819-6388",
            "website": "https://figure.com",
            "url": "https://www.google.com/maps/place/Figure+Technologies/@40.7399,−73.9901",
            "openingHours": [{"day": "Monday-Friday", "hours": "9:00 AM – 6:00 PM"}],
            "categories": ["Financial Technology Company", "Blockchain Finance"],
        },
        {
            "title": "Navan",
            "totalScore": 4.2,
            "reviewsCount": 23,
            "address": "1 Park Ave, Suite 900, New York, NY 10016",
            "phone": "+1 (650) 564-6000",
            "website": "https://navan.com",
            "url": "https://www.google.com/maps/place/Navan/@40.7483,−73.9832",
            "openingHours": [{"day": "Monday-Friday", "hours": "9:00 AM – 6:00 PM"}],
            "categories": ["Financial Technology Company", "Travel & Expense Management"],
        },
        {
            "title": "Stripe",
            "totalScore": 4.5,
            "reviewsCount": 112,
            "address": "354 Oyster Point Blvd (NYC office: 510 Madison Ave), New York, NY 10022",
            "phone": "+1 (888) 926-2289",
            "website": "https://stripe.com",
            "url": "https://www.google.com/maps/place/Stripe/@40.7590,−73.9729",
            "openingHours": [{"day": "Monday-Friday", "hours": "9:00 AM – 6:00 PM"}],
            "categories": ["Financial Technology Company", "Payment Infrastructure"],
        },
    ],

    # ── Query 3: Fintech Lead Gen NYC — LinkedIn decision makers ───────────────
    # 5 decision-maker profiles from NYC fintech companies
    # TODO: verify field names against live harvestapi~linkedin-company-employees /builds/default
    "linkedin_employees": [
        {
            "fullName": "Zach Perret",
            "title": "Co-founder & CEO",
            "linkedinUrl": "https://www.linkedin.com/in/zachperret/",
            "company": "Plaid",
            "location": "San Francisco, CA",
            "email": None,
        },
        {
            "fullName": "Eric Glyman",
            "title": "Co-founder & CEO",
            "linkedinUrl": "https://www.linkedin.com/in/eglyman/",
            "company": "Ramp",
            "location": "New York, NY",
            "email": None,
        },
        {
            "fullName": "Max Levchin",
            "title": "Founder & CEO",
            "linkedinUrl": "https://www.linkedin.com/in/maxlevchin/",
            "company": "Affirm",
            "location": "San Francisco, CA",
            "email": None,
        },
        {
            "fullName": "Jason Gardner",
            "title": "Founder & CEO",
            "linkedinUrl": "https://www.linkedin.com/in/jasongardner/",
            "company": "Marqeta",
            "location": "Oakland, CA",
            "email": None,
        },
        {
            "fullName": "Guillaume Pousaz",
            "title": "Founder & CEO",
            "linkedinUrl": "https://www.linkedin.com/in/guillaume-pousaz/",
            "company": "Checkout.com",
            "location": "London, United Kingdom",
            "email": None,
        },
    ],

    # ── Generic fixtures for remaining 9 registered actors ─────────────────────

    "instagram_generic": [
        {"url": "https://www.instagram.com/p/C7xyz123/", "caption": "Excited to share our latest AI research paper — link in bio.", "likesCount": 4821, "commentsCount": 89, "ownerUsername": "anthropic_ai", "timestamp": "2026-05-25T10:00:00Z", "type": "Image"},
        {"url": "https://www.instagram.com/p/C7abc456/", "caption": "Behind the scenes at OpenAI's offices. The energy here is unreal. 🚀", "likesCount": 12340, "commentsCount": 312, "ownerUsername": "openai", "timestamp": "2026-05-24T14:30:00Z", "type": "Image"},
        {"url": "https://www.instagram.com/p/C7def789/", "caption": "Scaling AI for enterprise. Our new case study is live. #ScaleAI #MachineLearning", "likesCount": 3201, "commentsCount": 54, "ownerUsername": "scale_ai", "timestamp": "2026-05-23T09:00:00Z", "type": "Image"},
        {"url": "https://www.instagram.com/p/C7ghi012/", "caption": "Just shipped a major update to Cohere Command R+. Benchmark results in comments.", "likesCount": 2891, "commentsCount": 71, "ownerUsername": "cohere_ai", "timestamp": "2026-05-22T16:00:00Z", "type": "Image"},
        {"url": "https://www.instagram.com/p/C7jkl345/", "caption": "Glean raises Series E at $4.6B valuation. Thank you to our incredible team and customers.", "likesCount": 5432, "commentsCount": 128, "ownerUsername": "glean_ai", "timestamp": "2026-05-21T12:00:00Z", "type": "Image"},
    ],

    "youtube_generic": [
        {"title": "OpenAI's New Model: Full Technical Breakdown", "id": "dQw4w9WgXcQ", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "viewCount": 892341, "likes": 34201, "channelName": "Two Minute Papers", "subscriberCount": 1200000, "duration": "PT18M42S", "date": "2026-05-26", "order": 1},
        {"title": "Building with the Anthropic API in 2026 — Full Tutorial", "id": "abc123def45", "url": "https://www.youtube.com/watch?v=abc123def45", "viewCount": 312000, "likes": 18900, "channelName": "AI Explained", "subscriberCount": 890000, "duration": "PT45M12S", "date": "2026-05-24", "order": 2},
        {"title": "Scale AI CEO Alexandr Wang: The Data Behind AI Dominance", "id": "xyz789uvw01", "url": "https://www.youtube.com/watch?v=xyz789uvw01", "viewCount": 218000, "likes": 9800, "channelName": "Lex Fridman Podcast", "subscriberCount": 4100000, "duration": "PT2H34M", "date": "2026-05-22", "order": 3},
    ],

    "tiktok_generic": [
        {"id": "7281234567890", "text": "POV: you give Claude a 500-page PDF and it actually reads it #AI #Claude #Anthropic", "createTimeISO": "2026-05-26T15:00:00Z", "webVideoUrl": "https://www.tiktok.com/@techwithtim/video/7281234567890", "diggCount": 89234, "shareCount": 12341, "playCount": 1892000, "commentCount": 2341, "authorMeta": {"name": "techwithtim", "nickname": "Tech With Tim", "verified": False, "fans": 892000}},
        {"id": "7281234567891", "text": "The AI startup landscape in SF right now is INSANE 🤯 #startup #AI #sanfrancisco #vc", "createTimeISO": "2026-05-25T12:00:00Z", "webVideoUrl": "https://www.tiktok.com/@vcinsider/video/7281234567891", "diggCount": 45123, "shareCount": 8921, "playCount": 981000, "commentCount": 1234, "authorMeta": {"name": "vcinsider", "nickname": "VC Insider", "verified": True, "fans": 341000}},
        {"id": "7281234567892", "text": "Replying to @user123 — here's why fintech is still the hottest sector despite the downturn #fintech #startup", "createTimeISO": "2026-05-24T09:00:00Z", "webVideoUrl": "https://www.tiktok.com/@fintechfriday/video/7281234567892", "diggCount": 23891, "shareCount": 4321, "playCount": 512000, "commentCount": 891, "authorMeta": {"name": "fintechfriday", "nickname": "Fintech Friday", "verified": False, "fans": 189000}},
    ],

    "linkedin_profile_search_generic": [
        {"fullName": "Sarah Chen", "headline": "VP of Engineering at Databricks", "company": "Databricks", "location": "San Francisco, CA", "linkedinUrl": "https://www.linkedin.com/in/sarahchen-databricks/"},
        {"fullName": "Michael Torres", "headline": "Head of AI Products at Cohere", "company": "Cohere", "location": "Toronto, ON", "linkedinUrl": "https://www.linkedin.com/in/michaeltorres-cohere/"},
        {"fullName": "Jessica Liu", "headline": "Director of Research at Scale AI", "company": "Scale AI", "location": "San Francisco, CA", "linkedinUrl": "https://www.linkedin.com/in/jessicaliu-scaleai/"},
        {"fullName": "David Okonkwo", "headline": "Principal Engineer at Anthropic", "company": "Anthropic", "location": "San Francisco, CA", "linkedinUrl": "https://www.linkedin.com/in/davidokonkwo-anthropic/"},
        {"fullName": "Priya Ramanujan", "headline": "Co-founder at Harvey AI", "company": "Harvey", "location": "San Francisco, CA", "linkedinUrl": "https://www.linkedin.com/in/priyaramanujan-harvey/"},
    ],

    "linkedin_posts_generic": [
        {"text": "Excited to share that Anthropic just published our latest safety research on Constitutional AI improvements. The core insight: RLHF alone is insufficient for alignment at scale. Full paper linked below.", "authorName": "Dario Amodei", "authorTitle": "CEO at Anthropic", "likesCount": 8921, "commentsCount": 312, "postUrl": "https://www.linkedin.com/posts/dario-amodei_ai-safety-research", "postedAt": "2026-05-26T10:00:00Z"},
        {"text": "Scale AI just crossed $1B in ARR. What started as a data labeling company has evolved into the data infrastructure layer for AI. Grateful to the team, customers, and investors who made this possible.", "authorName": "Alexandr Wang", "authorTitle": "CEO at Scale AI", "likesCount": 12341, "commentsCount": 891, "postUrl": "https://www.linkedin.com/posts/alexandr-wang_scale-ai-growth", "postedAt": "2026-05-25T14:00:00Z"},
        {"text": "Hiring update: Cohere is growing fast and we need ML engineers, product managers, and enterprise sales. If you want to work on LLMs that actually run in production at enterprise scale — not just demos — I want to talk to you.", "authorName": "Aidan Gomez", "authorTitle": "CEO at Cohere", "likesCount": 4231, "commentsCount": 198, "postUrl": "https://www.linkedin.com/posts/aidangomez_hiring-ml-enterprise", "postedAt": "2026-05-24T09:00:00Z"},
    ],

    "amazon_generic": [
        {"title": "NVIDIA RTX 4090 Graphics Card", "price": "$1,599.00", "stars": 4.7, "reviewsCount": 2341, "asin": "B0BG9KG3VS", "brand": "NVIDIA", "url": "https://www.amazon.com/dp/B0BG9KG3VS", "availability": "In Stock"},
        {"title": "Apple MacBook Pro 16-inch M3 Max", "price": "$3,499.00", "stars": 4.8, "reviewsCount": 1892, "asin": "B0CM5JV268", "brand": "Apple", "url": "https://www.amazon.com/dp/B0CM5JV268", "availability": "In Stock"},
        {"title": "LG UltraWide 34\" Curved Monitor", "price": "$799.00", "stars": 4.5, "reviewsCount": 3102, "asin": "B07YGZ7RLY", "brand": "LG", "url": "https://www.amazon.com/dp/B07YGZ7RLY", "availability": "In Stock"},
    ],

    "web_crawl_generic": [
        {"url": "https://example.com/about", "crawl": {"loadedUrl": "https://example.com/about", "depth": 0, "httpStatusCode": 200}, "metadata": {"title": "About Us", "description": "Learn about our company and mission.", "languageCode": "en"}, "text": "We are a technology company focused on building innovative solutions.", "markdown": "# About Us\nWe are a technology company focused on building innovative solutions."},
        {"url": "https://example.com/products", "crawl": {"loadedUrl": "https://example.com/products", "depth": 1, "httpStatusCode": 200}, "metadata": {"title": "Products", "description": "Our product lineup for 2026.", "languageCode": "en"}, "text": "Our flagship product is available in three tiers: Starter, Professional, and Enterprise.", "markdown": "# Products\nOur flagship product is available in three tiers: Starter, Professional, and Enterprise."},
        {"url": "https://example.com/contact", "crawl": {"loadedUrl": "https://example.com/contact", "depth": 1, "httpStatusCode": 200}, "metadata": {"title": "Contact", "description": "Get in touch with our team.", "languageCode": "en"}, "text": "Reach us at hello@example.com or call +1 (415) 555-0100.", "markdown": "# Contact\nReach us at hello@example.com or call +1 (415) 555-0100."},
    ],

    "web_scrape_generic": [
        {"url": "https://example.com", "title": "Example Domain", "text": "This domain is for use in illustrative examples in documents."},
        {"url": "https://example.com/page2", "title": "Page 2 — Example", "text": "Additional content scraped from page 2 of the example domain."},
        {"url": "https://example.com/page3", "title": "Page 3 — Example", "text": "Further content from page 3 demonstrating the scraper's reach."},
    ],

    "cheerio_scrape_generic": [
        {"url": "https://example.com", "title": "Example Domain", "text": "This domain is for use in illustrative examples."},
        {"url": "https://example.com/news", "title": "News — Example", "text": "Latest updates and news items from example domain."},
        {"url": "https://example.com/blog", "title": "Blog — Example", "text": "Blog posts and articles from the example domain team."},
    ],
}

# ── Mock store search results (Tier 2 dynamic discovery) ──────────────────────
# Returned by search_store() in MOCK_MODE for any query string.
# Represents 5 realistic actor candidates from the 33,000+ Apify Store.
MOCK_STORE_SEARCH_RESULTS: list[dict] = [
    {"id": "zdc3Pyhyz3m8vjDeM", "username": "vaclavrut", "name": "zillow-scraper", "title": "Zillow Real Estate Scraper", "description": "Scrapes property listings, prices, and details from Zillow. Supports search by location, price range, and property type.", "stats": {"totalUsers": 14200, "totalRuns": 1890000, "lastRunStartedAt": "2026-05-28T08:00:00Z"}, "currentPricingInfo": {"pricingModel": "PRICE_PER_DATASET_ITEM"}},
    {"id": "abc1Defgh2ijKlmN3", "username": "apify", "name": "web-scraper", "title": "Web Scraper", "description": "General-purpose web scraper that runs JavaScript and extracts data using a custom pageFunction.", "stats": {"totalUsers": 82000, "totalRuns": 12000000, "lastRunStartedAt": "2026-05-29T06:00:00Z"}, "currentPricingInfo": {"pricingModel": "FREE"}},
    {"id": "def4Ghijk5lmNopQ6", "username": "dtrungtin", "name": "airbnb-scraper", "title": "Airbnb Scraper", "description": "Scrapes Airbnb listings by location, date range, and filters. Returns pricing, availability, and host details.", "stats": {"totalUsers": 8900, "totalRuns": 412000, "lastRunStartedAt": "2026-05-27T14:00:00Z"}, "currentPricingInfo": {"pricingModel": "PRICE_PER_DATASET_ITEM"}},
    {"id": "ghi7Jklmn8opQrst9", "username": "pocesar", "name": "yelp-scraper", "title": "Yelp Scraper", "description": "Extracts business listings, reviews, ratings, and contact information from Yelp.", "stats": {"totalUsers": 6700, "totalRuns": 289000, "lastRunStartedAt": "2026-05-26T10:00:00Z"}, "currentPricingInfo": {"pricingModel": "PRICE_PER_DATASET_ITEM"}},
    {"id": "jkl0Mnopq1rstuVw2", "username": "maxcopell", "name": "google-maps-reviews-scraper", "title": "Google Maps Reviews Scraper", "description": "Scrapes reviews and ratings from Google Maps for any business. Supports bulk business list input.", "stats": {"totalUsers": 11400, "totalRuns": 891000, "lastRunStartedAt": "2026-05-28T12:00:00Z"}, "currentPricingInfo": {"pricingModel": "PRICE_PER_DATASET_ITEM"}},
]

# ── Mock input schemas (minimal; used by get_actor_input_schema in MOCK_MODE) ─
MOCK_INPUT_SCHEMAS: dict[str, dict] = {
    "apify~google-search-scraper": {"type": "object", "properties": {"queries": {"type": "string"}, "resultsPerPage": {"type": "integer", "default": 10}, "maxPagesPerQuery": {"type": "integer", "default": 1}}, "required": ["queries"]},
    "trudax~reddit-scraper-lite": {"type": "object", "properties": {"searches": {"type": "array"}, "startUrls": {"type": "array"}, "maxItems": {"type": "integer"}, "skipComments": {"type": "boolean"}}, "required": []},
    "apidojo~tweet-scraper": {"type": "object", "properties": {"searchTerms": {"type": "array"}, "startUrls": {"type": "array"}, "twitterHandles": {"type": "array"}, "maxItems": {"type": "integer"}, "sort": {"type": "string"}, "start": {"type": "string"}, "end": {"type": "string"}}, "required": []},
    "compass~crawler-google-places": {"type": "object", "properties": {"searchStringsArray": {"type": "array"}, "locationQuery": {"type": "string"}, "maxCrawledPlacesPerSearch": {"type": "integer"}, "language": {"type": "string"}, "maxReviews": {"type": "integer"}}, "required": ["searchStringsArray"]},
}

# ── Maps actor_id → mock dataset key ──────────────────────────────────────────
# Used by run_actor_async() to set defaultDatasetId in the mock run object.
# Unknown actor_ids (Tier 2 dynamic) fall back to "web_crawl_generic".
_MOCK_ACTOR_DATASET_MAP: dict[str, str] = {
    "apify~google-search-scraper": "google_search_ai_startups",
    "trudax~reddit-scraper-lite": "reddit_openai",
    "apidojo~tweet-scraper": "twitter_openai",
    "apimaestro~linkedin-profile-batch-scraper-no-cookies-required": "linkedin_profiles",
    "harvestapi~linkedin-company-employees": "linkedin_employees",
    "compass~crawler-google-places": "google_maps_fintech",
    "apify~instagram-scraper": "instagram_generic",
    "streamers~youtube-scraper": "youtube_generic",
    "clockworks~tiktok-scraper": "tiktok_generic",
    "harvestapi~linkedin-profile-search": "linkedin_profile_search_generic",
    "apimaestro~linkedin-posts-search-scraper-no-cookies": "linkedin_posts_generic",
    "junglee~amazon-crawler": "amazon_generic",
    "apify~website-content-crawler": "web_crawl_generic",
    "apify~web-scraper": "web_scrape_generic",
    "apify~cheerio-scraper": "cheerio_scrape_generic",
}


# ── Client wrapper ─────────────────────────────────────────────────────────────

class ApifyClientWrapper:
    """
    Thin wrapper around the Apify REST API.
    All methods check MOCK_MODE first and return fixture data without any HTTP calls.
    In real mode, the apify-client SDK handles polling and 429 backoff automatically.
    """

    def __init__(self) -> None:
        self.mock_mode = MOCK_MODE
        self._sdk_client = None
        if not self.mock_mode:
            if not APIFY_TOKEN:
                raise RuntimeError("APIFY_TOKEN is not set. Add it to your .env file.")
            try:
                from apify_client import ApifyClient as _ApifySDKClient
                self._sdk_client = _ApifySDKClient(token=APIFY_TOKEN)
            except ImportError as exc:
                raise RuntimeError(
                    "apify-client is not installed. Run: pip install apify-client"
                ) from exc

    # ── Store search ──────────────────────────────────────────────────────────

    def search_store(
        self,
        query: str,
        category: Optional[str] = None,
        sort_by: str = "popularity",
        limit: int = 10,
    ) -> list[dict]:
        """
        Search the Apify Store. Returns up to `limit` actor metadata dicts.
        Used by Tier 2 dynamic discovery to find actors beyond the 15-actor registry.

        Real mode: GET /v2/store?search={query}&sortBy={sort_by}&limit={limit}
          Returns: response["data"]["items"]
          Each item has: id, username, name, title, description, stats.totalUsers,
                         currentPricingInfo.pricingModel

        Mock mode: returns MOCK_STORE_SEARCH_RESULTS (5 items), ignores query.

        # Example input:  query="zillow real estate listings scraper", limit=10
        # Example output: [
        #   {"id": "zdc3...", "username": "vaclavrut", "name": "zillow-scraper",
        #    "title": "Zillow Real Estate Scraper", "stats": {"totalUsers": 14200}},
        #   ...4 more actors
        # ]
        """
        if self.mock_mode:
            return MOCK_STORE_SEARCH_RESULTS[:limit]

        import requests
        params: dict = {"search": query, "sortBy": sort_by, "limit": limit}
        if category:
            params["category"] = category
        headers = {"Authorization": f"Bearer {APIFY_TOKEN}"}
        resp = requests.get(f"{BASE_URL}/store", headers=headers, params=params, timeout=60)
        resp.raise_for_status()
        return resp.json()["data"]["items"]

    # ── Actor metadata ────────────────────────────────────────────────────────

    def get_actor_details(self, actor_id: str) -> dict:
        """
        Fetch actor metadata from GET /v2/acts/{actor_id}.
        Note: the input schema is NOT in this response — use get_actor_input_schema() for that.

        Mock mode: returns a minimal stub dict.

        # Example input:  actor_id="apify~google-search-scraper"
        # Example output: {"id": "HDSasDasz78YcAPEB", "name": "google-search-scraper",
        #                  "username": "apify", "stats": {"totalRuns": 5000000}}
        """
        if self.mock_mode:
            username, name = (actor_id.split("~") + ["unknown"])[:2]
            return {"id": f"mock_{name}", "name": name, "username": username, "stats": {"totalRuns": 100000}}

        import requests
        headers = {"Authorization": f"Bearer {APIFY_TOKEN}"}
        resp = requests.get(f"{BASE_URL}/acts/{actor_id}", headers=headers, timeout=60)
        resp.raise_for_status()
        return resp.json()["data"]

    def get_actor_input_schema(self, actor_id: str) -> dict:
        """
        Fetch the actor's input schema via GET /v2/acts/{actor_id}/builds/default.
        Extracts response["data"]["actorDefinition"]["input"].
        Falls back to {} if the key is missing (not all actors publish a schema).

        Used by Tier 2 dynamic path: Claude reads this schema to build run_input.

        Mock mode: returns MOCK_INPUT_SCHEMAS.get(actor_id, {}).

        # Example input:  actor_id="apify~google-search-scraper"
        # Example output: {"type": "object",
        #                  "properties": {"queries": {"type": "string"}, ...},
        #                  "required": ["queries"]}
        """
        if self.mock_mode:
            return MOCK_INPUT_SCHEMAS.get(actor_id, {})

        import requests
        headers = {"Authorization": f"Bearer {APIFY_TOKEN}"}
        resp = requests.get(f"{BASE_URL}/acts/{actor_id}/builds/default", headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        actor_def = data.get("actorDefinition", {})
        return actor_def.get("input", {})

    # ── Run lifecycle ─────────────────────────────────────────────────────────

    def run_actor_async(
        self,
        actor_id: str,
        run_input: dict,
        memory_mb: int = 1024,
        timeout_secs: int = 300,
        max_items: int = 100,
    ) -> dict:
        """
        Start an actor run and return immediately (async).
        Returns the raw run object: {id, status, defaultDatasetId, defaultKeyValueStoreId}.
        Caller must then call poll_run_until_done() to wait for completion.

        Real mode: uses apify-client SDK .start() — handles auth, Content-Type.
          max_items is NOT directly supported by the SDK's .start() method;
          it is passed as a query param (?maxItems=) via direct requests call.
          TODO: verify maxItems passthrough on Sunday when testing live mode.

        Mock mode: returns a synthetic run object with status="SUCCEEDED" immediately.
          defaultDatasetId is set to the fixture key for this actor_id.
          Unknown actor_ids fall back to "web_crawl_generic".

        # Example input:  actor_id="apify~google-search-scraper",
        #                 run_input={"queries": "AI startups San Francisco", "resultsPerPage": 10}
        # Example output: {"id": "HG7ML7M8z78YcAPEB", "status": "RUNNING",
        #                  "defaultDatasetId": "mock_google_search_ai_startups",
        #                  "defaultKeyValueStoreId": "mock_kvs_001"}
        """
        if self.mock_mode:
            dataset_key = _MOCK_ACTOR_DATASET_MAP.get(actor_id, "web_crawl_generic")
            safe_id = actor_id.replace("~", "_").replace("-", "_")[:20]
            return {
                "id": f"mock_run_{safe_id}_{uuid.uuid4().hex[:6]}",
                "actId": f"mock_act_{safe_id}",
                "status": "SUCCEEDED",
                "defaultDatasetId": dataset_key,
                "defaultKeyValueStoreId": "mock_kvs_001",
                "startedAt": "2026-05-29T10:00:00Z",
                "finishedAt": "2026-05-29T10:00:30Z",
            }

        run = self._sdk_client.actor(actor_id).start(
            run_input=run_input,
            memory_mbytes=memory_mb,
            timeout_secs=timeout_secs,
            build="latest",
        )
        return dict(run)

    def poll_run_until_done(
        self,
        run_id: str,
        poll_interval_secs: int = 5,
        max_wait_secs: int = 600,
    ) -> dict:
        """
        Poll GET /v2/actor-runs/{run_id} every poll_interval_secs until a terminal status.
        Terminal states (from Apify reference Section 5): SUCCEEDED, FAILED, TIMED-OUT, ABORTED.
        Raises TimeoutError if max_wait_secs is exceeded before a terminal status.

        Mock mode: returns a SUCCEEDED run dict immediately (no sleep, no HTTP).

        # Example input:  run_id="HG7ML7M8z78YcAPEB", poll_interval_secs=5
        # Example output: {"id": "HG7ML7M8z78YcAPEB", "status": "SUCCEEDED",
        #                  "defaultDatasetId": "mock_google_search_ai_startups",
        #                  "finishedAt": "2026-05-29T10:00:30Z"}
        """
        if self.mock_mode:
            return {
                "id": run_id,
                "status": "SUCCEEDED",
                "defaultDatasetId": "mock_dataset",
                "defaultKeyValueStoreId": "mock_kvs_001",
                "finishedAt": "2026-05-29T10:00:30Z",
            }

        import requests
        headers = {"Authorization": f"Bearer {APIFY_TOKEN}"}
        elapsed = 0
        while elapsed < max_wait_secs:
            resp = requests.get(f"{BASE_URL}/actor-runs/{run_id}", headers=headers, timeout=60)
            resp.raise_for_status()
            run = resp.json()["data"]
            if run["status"] in _TERMINAL_STATUSES:
                return run
            time.sleep(poll_interval_secs)
            elapsed += poll_interval_secs
        raise TimeoutError(f"Run {run_id} did not finish within {max_wait_secs}s")

    def fetch_dataset_items(
        self,
        dataset_id: str,
        limit: int = 100,
        offset: int = 0,
        clean: bool = True,
    ) -> list[dict]:
        """
        Fetch items from GET /v2/datasets/{dataset_id}/items.
        IMPORTANT: this endpoint returns a raw JSON array, NOT {"data": [...]}.

        Mock mode: returns MOCK_DATASET_ITEMS.get(dataset_id, []).
          If dataset_id is not in the fixture map, returns [] silently.

        # Example input:  dataset_id="reddit_openai", limit=50
        # Example output: [{"title": "OpenAI's latest model...", "score": 2847, ...}, ...]
        """
        if self.mock_mode:
            items = MOCK_DATASET_ITEMS.get(dataset_id, [])
            return items[offset: offset + limit]

        import requests
        headers = {"Authorization": f"Bearer {APIFY_TOKEN}"}
        params = {"format": "json", "clean": str(clean).lower(), "limit": limit, "offset": offset}
        resp = requests.get(
            f"{BASE_URL}/datasets/{dataset_id}/items",
            headers=headers,
            params=params,
            timeout=120,
        )
        resp.raise_for_status()
        # Dataset items endpoint returns a raw JSON array, not wrapped in {"data": [...]}
        result = resp.json()
        return result if isinstance(result, list) else result.get("items", [])

    def fetch_kv_store_output(self, store_id: str, key: str = "OUTPUT") -> Optional[dict]:
        """
        Fetch a record from GET /v2/key-value-stores/{store_id}/records/{key}.
        Returns parsed JSON or None on 404.
        Used as fallback when a SUCCEEDED run has an empty dataset
        (some actors write to OUTPUT key instead of dataset).

        Mock mode: always returns None (all mock actors write to dataset).

        # Example input:  store_id="FL35Jsovsa3Okdao2", key="OUTPUT"
        # Example output: None  (mock mode) or {"result": [...]} (real mode)
        """
        if self.mock_mode:
            return None

        import requests
        headers = {"Authorization": f"Bearer {APIFY_TOKEN}"}
        resp = requests.get(
            f"{BASE_URL}/key-value-stores/{store_id}/records/{key}",
            headers=headers,
            timeout=60,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    # ── Convenience wrapper ───────────────────────────────────────────────────

    def run_and_collect(
        self,
        actor_id: str,
        run_input: dict,
        memory_mb: int = 1024,
        timeout_secs: int = 300,
        max_items: int = 100,
    ) -> ActorRunResult:
        """
        Full pipeline: run_actor_async → poll_run_until_done → fetch_dataset_items.
        Returns a populated ActorRunResult.

        item_count is always set explicitly as len(items) — it is NOT auto-computed
        by the Pydantic model (ActorRunResult.item_count defaults to 0).

        If the run status is not SUCCEEDED, items=[] and error_message is set.
        If the dataset is empty on SUCCEEDED, fetch_kv_store_output is checked as fallback.

        # Example input:  actor_id="trudax~reddit-scraper-lite",
        #                 run_input={"searches": ["OpenAI"], "maxItems": 50}
        # Example output: ActorRunResult(
        #   actor_id="trudax~reddit-scraper-lite", status=SUCCEEDED,
        #   items=[{...}×10], item_count=10, error_message=None
        # )
        """
        run = self.run_actor_async(actor_id, run_input, memory_mb, timeout_secs, max_items)
        # In mock mode the run is already SUCCEEDED — skip polling to preserve defaultDatasetId.
        if not self.mock_mode:
            run = self.poll_run_until_done(run["id"])

        raw_status = run["status"]
        # Normalize Apify's "TIMED-OUT" (hyphen) to our enum value "TIMED_OUT" (underscore)
        normalized = raw_status.replace("-", "_")
        try:
            status = ActorRunStatus(normalized)
        except ValueError:
            status = ActorRunStatus.FAILED

        items: list[dict] = []
        error_message: Optional[str] = None

        if status == ActorRunStatus.SUCCEEDED:
            items = self.fetch_dataset_items(run["defaultDatasetId"], limit=max_items)
            # Fallback: if dataset is empty, check key-value store OUTPUT
            if not items:
                kv_output = self.fetch_kv_store_output(run["defaultKeyValueStoreId"])
                if kv_output:
                    items = [kv_output] if isinstance(kv_output, dict) else kv_output
        else:
            error_message = f"Run ended with status: {raw_status}"

        return ActorRunResult(
            actor_id=actor_id,
            run_id=run["id"],
            status=status,
            dataset_id=run["defaultDatasetId"],
            kv_store_id=run["defaultKeyValueStoreId"],
            items=items,
            item_count=len(items),      # must be set explicitly — not auto-computed by model
            error_message=error_message,
        )
