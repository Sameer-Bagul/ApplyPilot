"""Time-bounded search dork harvester for LinkedIn Posts, X, and Threads.

Executes search queries targeting fresh (past 24h) hiring posts across social
networks using public search engines (DuckDuckGo, Brave, Exa) with ZERO login
cookies and ZERO account ban risk.
"""

from __future__ import annotations

import html
import json
import logging
import os
import re
import urllib.parse
import urllib.request
from typing import Any

from applypilot import config

logger = logging.getLogger(__name__)

# Search dork templates for social hiring posts
DEFAULT_DORK_TEMPLATES = [
    {
        "platform": "linkedin",
        "dork": 'site:linkedin.com/posts ("we are hiring" OR "hiring" OR "looking for") ("send your resume" OR "mail" OR "@")',
    },
    {
        "platform": "x",
        "dork": 'site:x.com ("we are hiring" OR "hiring a" OR "send resume") ("email" OR "apply" OR "DM")',
    },
    {
        "platform": "threads",
        "dork": 'site:threads.net ("we are hiring" OR "hiring a" OR "looking for") ("email" OR "apply")',
    },
]

_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


def search_duckduckgo_html(query: str, max_results: int = 15, timeout: float = 10.0) -> list[dict[str, str]]:
    """Execute search query using ddgs library with fallback to DuckDuckGo HTML endpoint."""
    # 1. Try modern ddgs client (handles TLS fingerprints and anti-bot challenges)
    try:
        from ddgs import DDGS
        with DDGS(timeout=int(timeout)) as ddgs_client:
            raw_hits = list(ddgs_client.text(query, max_results=max_results))
            if raw_hits:
                results: list[dict[str, str]] = []
                for h in raw_hits:
                    results.append({
                        "title": h.get("title", ""),
                        "snippet": h.get("body", ""),
                        "url": h.get("href", ""),
                    })
                return results
    except Exception as e:
        logger.debug("ddgs client notice, trying raw HTML fallback: %s", e)

    # 2. Raw HTML fallback
    encoded_query = urllib.parse.urlencode({"q": query, "df": "d"})  # df=d means past day
    url = f"https://html.duckduckgo.com/html/?{encoded_query}"

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Referer": "https://html.duckduckgo.com/",
        },
    )

    results: list[dict[str, str]] = []
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8", errors="replace")

        # Parse result blocks using regex for lightweight parsing
        result_blocks = re.findall(
            r'<a class="result__url" href="([^"]+)".*?<a class="result__snippet[^>]*>(.*?)</a>',
            content,
            re.DOTALL | re.IGNORECASE,
        )
        for link, snippet_raw in result_blocks[:max_results]:
            # DuckDuckGo redirect decode
            actual_url = link
            if "uddg=" in link:
                match = re.search(r"uddg=([^&]+)", link)
                if match:
                    actual_url = urllib.parse.unquote(match.group(1))

            snippet = html.unescape(re.sub(r"<[^>]+>", "", snippet_raw).strip())
            results.append({
                "title": "",
                "snippet": snippet,
                "url": actual_url,
            })
    except Exception as e:
        logger.warning("DuckDuckGo search error for '%s': %s", query, e)

    return results


def search_brave(query: str, api_key: str, max_results: int = 15) -> list[dict[str, str]]:
    """Query Brave Search API if API key is provided."""
    encoded_query = urllib.parse.urlencode({"q": query, "count": max_results, "freshness": "pd"})
    url = f"https://api.search.brave.com/res/v1/web/search?{encoded_query}"
    req = urllib.request.Request(
        url,
        headers={
            "X-Subscription-Token": api_key,
            "Accept": "application/json",
        },
    )
    results = []
    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for item in data.get("web", {}).get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("description", ""),
                    "url": item.get("url", ""),
                })
    except Exception as e:
        logger.warning("Brave search error: %s", e)
    return results


def run_social_dorks(
    role_keywords: list[str] | None = None,
    platforms: list[str] | None = None,
    max_results_per_dork: int = 10,
) -> list[dict[str, Any]]:
    """Run time-filtered search dorks across LinkedIn, X, and Threads.

    Args:
        role_keywords: Optional extra keywords (e.g. ['Python', 'AI Engineer']).
        platforms: List of platforms to query (['linkedin', 'x', 'threads']).
        max_results_per_dork: Max results per dork query.

    Returns:
        List of candidate post dicts:
        {"title": ..., "text": ..., "url": ..., "platform": ...}
    """
    brave_key = os.environ.get("BRAVE_API_KEY")
    target_platforms = set(platforms or ["linkedin", "x", "threads"])

    discovered_posts: list[dict[str, Any]] = []
    role_clause = ""
    if role_keywords:
        role_clause = " (" + " OR ".join(f'"{r}"' for r in role_keywords[:3]) + ")"

    for item in DEFAULT_DORK_TEMPLATES:
        platform = item["platform"]
        if platform not in target_platforms:
            continue

        query = f"{item['dork']}{role_clause}"

        # Fetch results
        if brave_key:
            hits = search_brave(query, brave_key, max_results=max_results_per_dork)
        else:
            hits = search_duckduckgo_html(query, max_results=max_results_per_dork)

        for hit in hits:
            discovered_posts.append({
                "title": hit.get("title", ""),
                "text": hit.get("snippet", ""),
                "url": hit.get("url", ""),
                "platform": platform,
            })

    logger.info("Social dorks harvested %d candidate posts", len(discovered_posts))
    return discovered_posts
