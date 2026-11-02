"""Part 1A: Omni-Channel Social Discovery module."""

from applypilot.social_discovery.extractor import (
    extract_emails,
    extract_ats_urls,
    extract_all_urls,
    extract_evidence_snippet,
    classify_contact_type,
    classify_execution_route,
    parse_social_post,
)
from applypilot.social_discovery.reddit_scraper import (
    scrape_reddit_hiring_posts,
    fetch_subreddit_posts,
)
from applypilot.social_discovery.dork_searcher import (
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
]
