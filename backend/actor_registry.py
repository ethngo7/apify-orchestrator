from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from backend.models import ParsedIntent

# ── Actor Registry (Tier 1 Foundation) ────────────────────────────────────────
# 15 hardcoded curated actors sourced exclusively from technical reference Section 6.
# These are the FOUNDATION — the ceiling is 33,000+ actors via the Apify Store.
# When a query cannot be served by any entry here, get_chain_for_query() returns []
# and agent.py triggers dynamic Tier 2 store search.
#
# To add a new actor: add an entry here, add a mock fixture in apify_client.py,
# and update the "All 15 Registered Actors" table in CLAUDE.md.

ACTOR_REGISTRY: dict[str, dict] = {

    # ── Search & General Scraping ──────────────────────────────────────────────

    "apify~google-search-scraper": {
        # ref Section 6.3
        "title": "Google Search Scraper",
        "description": "Crawls Google SERPs — organic results, ads, People Also Ask, related queries.",
        "category": "search",
        "platforms": ["Google", "SERP"],
        "required_fields": ["queries"],
        "default_input": {"resultsPerPage": 10, "maxPagesPerQuery": 1},
        "mock_dataset_key": "google_search_ai_startups",
    },

    "apify~website-content-crawler": {
        # ref Section 6.1 — 117K users, 4.47★ on Store
        "title": "Website Content Crawler",
        "description": "Deep-crawls sites and converts HTML to Markdown/text for LLM/RAG pipelines.",
        "category": "web",
        "platforms": ["Web"],
        "required_fields": ["startUrls"],
        "default_input": {"crawlerType": "cheerio", "maxCrawlDepth": 1, "maxCrawlPages": 10},
        "mock_dataset_key": "web_crawl_generic",
    },

    "apify~web-scraper": {
        # ref Section 6.2 — full Chrome/Puppeteer + custom JS pageFunction
        "title": "Web Scraper",
        "description": "Universal scraper: runs full Chrome with a custom JavaScript pageFunction.",
        "category": "web",
        "platforms": ["Web"],
        "required_fields": ["startUrls", "pageFunction"],
        "default_input": {"maxPagesPerCrawl": 10},
        "mock_dataset_key": "web_scrape_generic",
    },

    "apify~cheerio-scraper": {
        # ref Section 6.2 — ~20× faster than web-scraper for static HTML
        "title": "Cheerio Scraper",
        "description": "Fast raw-HTTP scraper using Cheerio (jQuery-like) for static HTML pages.",
        "category": "web",
        "platforms": ["Web"],
        "required_fields": ["startUrls", "pageFunction"],
        "default_input": {"maxPagesPerCrawl": 20},
        "mock_dataset_key": "cheerio_scrape_generic",
    },

    # ── Social Media ───────────────────────────────────────────────────────────

    "trudax~reddit-scraper-lite": {
        # ref Section 6.8 — pay-per-result, ~$3.40/1,000 items
        "title": "Reddit Scraper Lite",
        "description": "Crawls Reddit posts, comments, communities, and users — no login required.",
        "category": "social",
        "platforms": ["Reddit"],
        "required_fields": [],   # searches OR startUrls — both optional per reference
        "default_input": {"maxItems": 50, "skipComments": False},
        "mock_dataset_key": "reddit_openai",
        # NOTE: "searches" field = plain string array per reference Section 6.8
        # TODO: confirm string vs object array against live /builds/default on Sunday
    },

    "apidojo~tweet-scraper": {
        # ref Section 6.5 — Actor numeric ID: "61RPP7dywgiy0JPD0", ~51K users, 3.9★
        # Use the named form "apidojo~tweet-scraper" — SDK resolves it.
        "title": "Tweet Scraper V2",
        "description": "Scrapes tweets by search term, handle, URL, or list. $0.40/1,000 tweets.",
        "category": "social",
        "platforms": ["Twitter", "X"],
        "required_fields": [],   # need at least one of: startUrls/searchTerms/twitterHandles
        "default_input": {"maxItems": 50, "sort": "Latest"},
        "mock_dataset_key": "twitter_openai",
        # NOTE: start/end date params only work with searchTerms — confirmed ref Section 6.5
    },

    "apify~instagram-scraper": {
        # ref Section 6.6 — 231K users, 4.73★ on Store
        "title": "Instagram Scraper",
        "description": "Scrapes Instagram profiles, posts, comments, hashtags, and places.",
        "category": "social",
        "platforms": ["Instagram"],
        "required_fields": [],   # directUrls OR search+searchType required
        "default_input": {"resultsType": "posts", "resultsLimit": 20},
        "mock_dataset_key": "instagram_generic",
    },

    "streamers~youtube-scraper": {
        # ref Section 6.9 — ~$5/1,000 videos, no YouTube API quota limits
        "title": "YouTube Scraper",
        "description": "Scrapes YouTube videos, channels, search results, and subtitles without quota.",
        "category": "social",
        "platforms": ["YouTube"],
        "required_fields": ["proxyConfiguration"],   # REQUIRED per reference Section 6.9
        "default_input": {"maxResults": 20},
        "mock_dataset_key": "youtube_generic",
    },

    "clockworks~tiktok-scraper": {
        # ref Section 6.10 — Actor ID: "GdWCkxBtKWOsKjdch", from $1.70/1,000
        "title": "TikTok Scraper",
        "description": "Scrapes TikTok by profile, hashtag, search, or video URL.",
        "category": "social",
        "platforms": ["TikTok"],
        "required_fields": [],   # profiles, hashtags, searchQueries, or postURLs
        "default_input": {"resultsPerPage": 20},
        "mock_dataset_key": "tiktok_generic",
    },

    # ── LinkedIn (no-cookie family) ────────────────────────────────────────────

    "apimaestro~linkedin-profile-batch-scraper-no-cookies-required": {
        # ref Section 6.4 — bulk profile scrape by URL, ~$5/1,000 profiles
        "title": "LinkedIn Profile Batch Scraper",
        "description": "Scrapes LinkedIn profiles in bulk by URL — no cookies required.",
        "category": "linkedin",
        "platforms": ["LinkedIn", "Profiles"],
        "required_fields": ["urls"],
        # TODO: verify "urls" field name against live /builds/default before Sunday run
        "default_input": {},
        "mock_dataset_key": "linkedin_profiles",
    },

    "harvestapi~linkedin-profile-search": {
        # ref Section 6.4 — search by company, title, location; caps at ~2,500/query
        "title": "LinkedIn Profile Search",
        "description": "Search LinkedIn profiles by company, title, and location filters.",
        "category": "linkedin",
        "platforms": ["LinkedIn", "Profiles"],
        "required_fields": [],   # filters: company, title, location
        "default_input": {},
        "mock_dataset_key": "linkedin_profile_search_generic",
        # NOTE: LinkedIn caps any single query at ~2,500 results — ref Section 6.4
    },

    "harvestapi~linkedin-company-employees": {
        # ref Section 6.4 — Short $4/1k, Full $8/1k, Full+email $12/1k
        "title": "LinkedIn Company Employees",
        "description": "Scrapes employee lists from LinkedIn company pages by company URL or name.",
        "category": "linkedin",
        "platforms": ["LinkedIn", "Employees"],
        "required_fields": ["companyUrls"],
        # TODO: verify "companyUrls" field name against live /builds/default on Sunday
        "default_input": {"mode": "Short"},
        # TODO: verify "mode" field name against live /builds/default on Sunday
        "mock_dataset_key": "linkedin_employees",
    },

    "apimaestro~linkedin-posts-search-scraper-no-cookies": {
        # ref Section 6.4 — LinkedIn post search without cookies
        "title": "LinkedIn Posts Search Scraper",
        "description": "Searches and scrapes LinkedIn posts by keyword — no cookies required.",
        "category": "linkedin",
        "platforms": ["LinkedIn", "Posts"],
        "required_fields": [],
        "default_input": {},
        "mock_dataset_key": "linkedin_posts_generic",
    },

    # ── E-Commerce & Local ─────────────────────────────────────────────────────

    "junglee~amazon-crawler": {
        # ref Section 6.7 — maintained by Apify, from $3/1,000 results
        "title": "Amazon Product Scraper",
        "description": "Scrapes Amazon product data by category, search, or product URL.",
        "category": "ecommerce",
        "platforms": ["Amazon"],
        "required_fields": ["categoryOrProductUrls"],
        "default_input": {"maxItemsPerStartUrl": 20, "scrapeProductDetails": True},
        "mock_dataset_key": "amazon_generic",
    },

    "compass~crawler-google-places": {
        # ref Section 6.11 — 361K users (largest on Store), 4.76★
        "title": "Google Maps Scraper",
        "description": "Scrapes Google Maps places — far beyond the 60-result official API cap.",
        "category": "local",
        "platforms": ["Google Maps", "Maps", "Places"],
        "required_fields": ["searchStringsArray"],
        "default_input": {"maxCrawledPlacesPerSearch": 50, "language": "en", "maxReviews": 0},
        "mock_dataset_key": "google_maps_fintech",
    },
}

# ── Demo query chains (Tier 1 fast path) ──────────────────────────────────────
# Deterministic actor sequences for the 3 primary demo queries.
# classify_demo_query() routes to one of these keys; no Claude call needed.

DEMO_QUERY_CHAINS: dict[str, list[str]] = {
    "ai_startups_sf": [
        "apify~google-search-scraper",
        "apimaestro~linkedin-profile-batch-scraper-no-cookies-required",
        "trudax~reddit-scraper-lite",
    ],
    "reddit_twitter_sentiment": [
        "trudax~reddit-scraper-lite",
        "apidojo~tweet-scraper",
    ],
    "fintech_lead_gen": [
        "compass~crawler-google-places",
        "harvestapi~linkedin-company-employees",
    ],
}

# Platform → actor_id priority map for non-demo Tier 1 queries.
# First match per platform wins; order matters.
_PLATFORM_ACTOR_MAP: list[tuple[list[str], str]] = [
    (["Reddit"],                                "trudax~reddit-scraper-lite"),
    (["Twitter", "X"],                          "apidojo~tweet-scraper"),
    (["Instagram"],                             "apify~instagram-scraper"),
    (["YouTube"],                               "streamers~youtube-scraper"),
    (["TikTok"],                                "clockworks~tiktok-scraper"),
    (["LinkedIn", "Profiles", "Employees"],     "apimaestro~linkedin-profile-batch-scraper-no-cookies-required"),
    (["LinkedIn Posts"],                        "apimaestro~linkedin-posts-search-scraper-no-cookies"),
    (["Google Maps", "Maps", "Places"],         "compass~crawler-google-places"),
    (["Amazon"],                                "junglee~amazon-crawler"),
    (["Google", "SERP"],                        "apify~google-search-scraper"),
    (["Web"],                                   "apify~website-content-crawler"),
]


# ── Query routing ──────────────────────────────────────────────────────────────

def classify_demo_query(user_query: str) -> Optional[str]:
    """
    Deterministic keyword classifier for the 3 primary demo queries.
    Returns a DEMO_QUERY_CHAINS key, or None if no demo pattern matches.
    No Claude call — pure string matching. Case-insensitive.

    # Example input:  "What are people saying about OpenAI on Reddit and Twitter this week?"
    # Example output: "reddit_twitter_sentiment"

    # Example input:  "Find top AI startups in SF, founders' LinkedIn, Reddit sentiment"
    # Example output: "ai_startups_sf"

    # Example input:  "Scrape Zillow listings in Austin TX"
    # Example output: None
    """
    q = user_query.lower()

    # Query 1: AI startups SF — needs LinkedIn + (Reddit or SF/startup keywords)
    if ("linkedin" in q and ("startup" in q or "founder" in q)
            and ("reddit" in q or " sf" in q or "san francisco" in q)):
        return "ai_startups_sf"

    # Query 2: Reddit + Twitter sentiment
    if "reddit" in q and ("twitter" in q or " x " in q or "tweet" in q):
        return "reddit_twitter_sentiment"

    # Query 3: Fintech lead gen — needs LinkedIn + (lead or fintech or google maps)
    if "linkedin" in q and ("lead" in q or "fintech" in q or "google maps" in q
                            or "decision maker" in q):
        return "fintech_lead_gen"

    return None


def get_chain_for_query(user_query: str, intent: ParsedIntent) -> list[str]:
    """
    Two-tier actor lookup. Always tries Tier 1 (registry) first.

    TIER 1a — Demo query match (deterministic, no Claude):
      classify_demo_query → DEMO_QUERY_CHAINS key → return chain

    TIER 1b — Platform-to-actor mapping (registry):
      For each platform in intent.platforms, find the first matching actor_id
      in _PLATFORM_ACTOR_MAP. Returns the de-duplicated ordered list.

    TIER 2 signal — no match:
      Returns [] to signal agent.py to trigger dynamic store search.

    # Example input (Tier 1a): user_query="AI startups SF founders LinkedIn Reddit"
    # Example output: ["apify~google-search-scraper",
    #                  "apimaestro~linkedin-profile-batch-scraper-no-cookies-required",
    #                  "trudax~reddit-scraper-lite"]

    # Example input (Tier 1b): intent.platforms=["Instagram", "YouTube"]
    # Example output: ["apify~instagram-scraper", "streamers~youtube-scraper"]

    # Example input (Tier 2): intent.platforms=["Zillow"], no demo match
    # Example output: []  ← triggers dynamic discovery in agent.py
    """
    # Tier 1a: demo query chains
    demo_key = classify_demo_query(user_query)
    if demo_key:
        return DEMO_QUERY_CHAINS[demo_key]

    # Tier 1b: platform mapping
    chain: list[str] = []
    seen: set[str] = set()
    for platform in intent.platforms:
        for platform_aliases, actor_id in _PLATFORM_ACTOR_MAP:
            if any(platform.lower() == alias.lower() for alias in platform_aliases):
                if actor_id not in seen:
                    chain.append(actor_id)
                    seen.add(actor_id)
                break

    return chain  # empty list → Tier 2 signal


def is_registered_actor(actor_id: str) -> bool:
    """
    Returns True if actor_id exists in ACTOR_REGISTRY (Tier 1 foundation).
    Used by agent.py to decide whether to use build_actor_input()
    or trigger dynamic input construction via Claude (Tier 2).

    # Example input:  actor_id="apify~google-search-scraper"
    # Example output: True

    # Example input:  actor_id="some_user~zillow-scraper"
    # Example output: False
    """
    return actor_id in ACTOR_REGISTRY


def get_registered_actor(actor_id: str) -> Optional[dict]:
    """
    Returns the ACTOR_REGISTRY entry for actor_id, or None if not registered.

    # Example input:  actor_id="compass~crawler-google-places"
    # Example output: {"title": "Google Maps Scraper", "platforms": ["Google Maps", ...],
    #                  "required_fields": ["searchStringsArray"], ...}
    """
    return ACTOR_REGISTRY.get(actor_id)


# ── Input builders ─────────────────────────────────────────────────────────────

def extract_linkedin_urls(serp_items: list[dict]) -> list[str]:
    """
    Extracts LinkedIn /in/ profile URLs from Google SERP organicResults.
    Used to chain google-search-scraper output → linkedin-profile-batch-scraper input.
    Returns up to 20 unique URLs. Skips /company/, /jobs/, and other non-profile paths.

    # Example input:  [{"organicResults": [
    #   {"url": "https://www.linkedin.com/in/dario-amodei/", "title": "Dario Amodei - Anthropic"},
    #   {"url": "https://techcrunch.com/2024/anthropic-funding", "title": "Anthropic raises $7.3B"},
    #   {"url": "https://www.linkedin.com/in/alexandr-wang-183601a1/", "title": "Alexandr Wang - Scale AI"}
    # ]}]
    # Example output: ["https://www.linkedin.com/in/dario-amodei/",
    #                  "https://www.linkedin.com/in/alexandr-wang-183601a1/"]
    """
    seen: set[str] = set()
    urls: list[str] = []
    for item in serp_items:
        for result in item.get("organicResults", []):
            url: str = result.get("url", "")
            if "linkedin.com/in/" in url and url not in seen:
                seen.add(url)
                urls.append(url)
                if len(urls) >= 20:
                    return urls
    return urls


def build_actor_input(
    actor_id: str,
    intent: ParsedIntent,
    prev_results: Optional[list[dict]] = None,
) -> dict:
    """
    Constructs the run_input dict for a registered (Tier 1) actor.
    Only used when is_registered_actor(actor_id) is True.
    For Tier 2 actors, Claude constructs input from the live schema.

    prev_results: items from the immediately preceding step, used for chaining.
      e.g. Google SERP items → LinkedIn URLs for the LinkedIn profile scraper.

    # Example input:  actor_id="trudax~reddit-scraper-lite",
    #                 intent=ParsedIntent(targets=["OpenAI"], time_range="this week")
    # Example output: {"searches": ["OpenAI"], "maxItems": 50, "skipComments": False}

    # Example input:  actor_id="apidojo~tweet-scraper",
    #                 intent=ParsedIntent(targets=["OpenAI"], time_range="this week")
    # Example output: {"searchTerms": ["OpenAI"], "maxItems": 50, "sort": "Latest",
    #                  "start": "2026-05-23"}
    """
    targets = intent.targets or []
    locations = intent.locations or []
    location_str = ", ".join(locations) if locations else "United States"

    # ── Google Search ──────────────────────────────────────────────────────────
    if actor_id == "apify~google-search-scraper":
        q_parts = targets + locations
        if intent.intent_type == "research":
            q_parts.append("founders LinkedIn")
        query = " ".join(q_parts).strip()
        return {"queries": query, "resultsPerPage": 10, "maxPagesPerQuery": 1}

    # ── Website Content Crawler ────────────────────────────────────────────────
    if actor_id == "apify~website-content-crawler":
        if prev_results:
            start_urls = [{"url": r.get("url", r.get("website", ""))} for r in prev_results[:5] if r.get("url") or r.get("website")]
        else:
            start_urls = [{"url": f"https://www.google.com/search?q={'+'.join(targets)}"}]
        return {
            "startUrls": start_urls,
            "crawlerType": "cheerio",
            "maxCrawlDepth": 1,
            "maxCrawlPages": 10,
        }

    # ── Web Scraper (custom JS) ────────────────────────────────────────────────
    if actor_id in ("apify~web-scraper", "apify~cheerio-scraper"):
        if prev_results:
            start_urls = [{"url": r.get("url", "")} for r in prev_results[:5] if r.get("url")]
        else:
            start_urls = [{"url": f"https://www.google.com/search?q={'+'.join(targets)}"}]
        # Minimal pageFunction: extract title + text content
        page_fn = "async function pageFunction(context) { const { $, request } = context; return { url: request.url, title: $('title').text().trim(), text: $('body').text().trim().slice(0, 2000) }; }"
        return {
            "startUrls": start_urls,
            "pageFunction": page_fn,
            "maxPagesPerCrawl": 10 if actor_id == "apify~web-scraper" else 20,
        }

    # ── Reddit ─────────────────────────────────────────────────────────────────
    if actor_id == "trudax~reddit-scraper-lite":
        # TODO: confirm "searches" field accepts plain string array (not object array)
        #       against live /builds/default on Sunday
        return {"searches": targets, "maxItems": 50, "skipComments": False}

    # ── Twitter / X ───────────────────────────────────────────────────────────
    if actor_id == "apidojo~tweet-scraper":
        inp: dict = {"searchTerms": targets, "maxItems": 50, "sort": "Latest"}
        # start/end date only work with searchTerms — confirmed ref Section 6.5
        if intent.time_range == "this week":
            inp["start"] = (date.today() - timedelta(days=7)).isoformat()
        elif intent.time_range == "last month":
            inp["start"] = (date.today() - timedelta(days=30)).isoformat()
        return inp

    # ── Instagram ─────────────────────────────────────────────────────────────
    if actor_id == "apify~instagram-scraper":
        if prev_results:
            # Chain from prior step: use URLs from previous results
            urls = [r.get("url", r.get("website", "")) for r in prev_results[:5] if r.get("url") or r.get("website")]
            return {"directUrls": urls, "resultsType": "posts", "resultsLimit": 20}
        # Fallback: use the first target as a search term
        return {"search": targets[0] if targets else "", "searchType": "hashtag", "resultsType": "posts", "resultsLimit": 20}

    # ── YouTube ───────────────────────────────────────────────────────────────
    if actor_id == "streamers~youtube-scraper":
        keywords = " ".join(targets)
        # proxyConfiguration is REQUIRED per reference Section 6.9
        return {
            "searchKeywords": keywords,
            "maxResults": 20,
            "proxyConfiguration": {"useApifyProxy": True},
        }

    # ── TikTok ────────────────────────────────────────────────────────────────
    if actor_id == "clockworks~tiktok-scraper":
        return {"searchQueries": targets, "resultsPerPage": 20}

    # ── LinkedIn Profile Batch ─────────────────────────────────────────────────
    if actor_id == "apimaestro~linkedin-profile-batch-scraper-no-cookies-required":
        if prev_results:
            linkedin_urls = extract_linkedin_urls(prev_results)
        else:
            # Fallback: construct profile URLs from target names
            linkedin_urls = [
                f"https://www.linkedin.com/in/{t.lower().replace(' ', '-')}/"
                for t in targets
            ]
        # TODO: verify field name "urls" against live /builds/default on Sunday
        return {"urls": linkedin_urls}

    # ── LinkedIn Profile Search ────────────────────────────────────────────────
    if actor_id == "harvestapi~linkedin-profile-search":
        inp = {}
        if targets:
            # TODO: verify exact field names for company/title/location filters on Sunday
            inp["VERIFY_FIELD_NAME_company"] = targets[0]
        if locations:
            inp["VERIFY_FIELD_NAME_location"] = location_str
        return inp

    # ── LinkedIn Company Employees ─────────────────────────────────────────────
    if actor_id == "harvestapi~linkedin-company-employees":
        if prev_results:
            company_names = [
                p.get("title", p.get("fullName", ""))
                for p in prev_results[:20]
                if p.get("title") or p.get("fullName")
            ]
        else:
            company_names = targets
        # TODO: verify field name "companyUrls" against live /builds/default on Sunday
        # TODO: verify "mode" field name against live /builds/default on Sunday
        return {"companyUrls": company_names, "mode": "Short"}

    # ── LinkedIn Posts ─────────────────────────────────────────────────────────
    if actor_id == "apimaestro~linkedin-posts-search-scraper-no-cookies":
        # TODO: verify input field name for keyword search against live /builds/default
        return {"VERIFY_FIELD_NAME_keywords": " ".join(targets)}

    # ── Amazon ─────────────────────────────────────────────────────────────────
    if actor_id == "junglee~amazon-crawler":
        # Build an Amazon search URL from the targets
        search_term = "+".join(targets)
        search_url = f"https://www.amazon.com/s?k={search_term}"
        return {
            "categoryOrProductUrls": [{"url": search_url}],
            "maxItemsPerStartUrl": 20,
            "scrapeProductDetails": True,
        }

    # ── Google Maps ────────────────────────────────────────────────────────────
    if actor_id == "compass~crawler-google-places":
        return {
            "searchStringsArray": targets,
            "locationQuery": location_str,
            "maxCrawledPlacesPerSearch": 50,
            "language": "en",
            "maxReviews": 0,
        }

    # Fallback: return registry defaults if actor_id is registered but has no specific logic
    entry = ACTOR_REGISTRY.get(actor_id, {})
    return dict(entry.get("default_input", {}))
