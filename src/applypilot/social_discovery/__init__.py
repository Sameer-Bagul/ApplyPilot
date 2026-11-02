"""Part 1A: Omni-Channel Social Discovery module (Facade).

Unified implementation resides in applypilot.discovery.
This module maintains 100% backward compatibility for all existing imports.
"""

from applypilot.discovery.lead_extractor import (
    classify_contact_type,
    classify_execution_route,
    extract_all_urls,
    extract_ats_urls,
    extract_emails,
    extract_evidence_snippet,
    parse_social_post,
)
from applypilot.discovery.omni_orchestrator import run_omni_channel_discovery
from applypilot.discovery.reddit_scraper import (
    fetch_subreddit_posts,
    scrape_reddit_hiring_posts,
)
from applypilot.discovery.social_dorker import (
    run_social_dorks,
    search_duckduckgo_html,
)

__all__ = [
    "extract_emails",
    "extract_ats_urls",
    "extract_all_urls",
    "extract_evidence_snippet",
    "classify_contact_type",
    "classify_execution_route",
    "parse_social_post",
    "scrape_reddit_hiring_posts",
    "fetch_subreddit_posts",
    "run_social_dorks",
    "search_duckduckgo_html",
    "run_omni_channel_discovery",
]
