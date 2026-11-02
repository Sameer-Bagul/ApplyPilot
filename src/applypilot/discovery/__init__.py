"""Unified Job & Social Discovery Engine for ApplyPilot.

Provides comprehensive discovery channels across:
- Backbone Indexes: Common Crawl CDX, open-apply-jobs, crt.sh
- Direct ATS Public Feeds: Greenhouse, Lever, Ashby, Workday
- Social Hiring Radar: Reddit, LinkedIn Guest, HackerNews, 24h Search Dorks
- Entity Extraction & Route Classification: Email extraction, ATS URL parsing
- Company Resolver: Website -> /careers -> ATS form resolver
"""

from __future__ import annotations

from applypilot.discovery.ats_direct_feeds import (
    poll_ashby_board,
    poll_board,
    poll_greenhouse_board,
    poll_lever_board,
    poll_watchlist,
)
from applypilot.discovery.cdx_harvester import (
    bootstrap_from_open_apply_jobs,
    extract_jobpostings_from_html,
    extract_slug_from_ats_url,
    get_latest_common_crawl_index,
    harvest_common_crawl_slugs,
    harvest_crtsh_career_subdomains,
    harvest_sitemap_career_urls,
    read_open_apply_parquet,
    sync_slugs_to_watchlist,
)
from applypilot.discovery.company_resolver import (
    extract_ats_from_page,
    resolve_company_ats,
    resolve_company_career_page,
    unshorten_url,
)
from applypilot.discovery.hackernews_harvester import (
    harvest_hackernews_who_is_hiring,
    scrape_hn_hiring_posts,
)
from applypilot.discovery.smartextract import run_smart_extract
from applypilot.discovery.lead_extractor import (
    classify_contact_type,
    classify_execution_route,
    extract_ats_urls,
    extract_emails,
    extract_evidence_snippet,
    parse_social_post,
)
from applypilot.discovery.bangalore_map_harvester import (
    enrich_startup_website_emails,
    fetch_bangalore_map_raw,
    fetch_company_deep_profile,
    generate_linkedin_connection_note,
    import_bangalore_startups_to_watchlist,
    parse_bangalore_map_rsc,
)
from applypilot.discovery.linkedin_guest import scrape_linkedin_guest_jobs
from applypilot.discovery.omni_orchestrator import run_omni_channel_discovery
from applypilot.discovery.reddit_scraper import (
    fetch_subreddit_hiring_posts,
    is_hiring_post,
)
from applypilot.discovery.social_dorker import (
    execute_social_dorks,
    search_duckduckgo_html,
)

__all__ = [
    # ATS direct feeds
    "poll_greenhouse_board",
    "poll_lever_board",
    "poll_ashby_board",
    "poll_board",
    "poll_watchlist",
    # CDX harvester
    "get_latest_common_crawl_index",
    "extract_slug_from_ats_url",
    "harvest_common_crawl_slugs",
    "harvest_crtsh_career_subdomains",
    "harvest_sitemap_career_urls",
    "bootstrap_from_open_apply_jobs",
    "read_open_apply_parquet",
    "extract_jobpostings_from_html",
    "sync_slugs_to_watchlist",
    # Company resolver
    "unshorten_url",
    "resolve_company_career_page",
    "extract_ats_from_page",
    "resolve_company_ats",
    # Social radar
    "fetch_subreddit_hiring_posts",
    "is_hiring_post",
    "scrape_linkedin_guest_jobs",
    "harvest_hackernews_who_is_hiring",
    "execute_social_dorks",
    "search_duckduckgo_html",
    # Extraction & Classification
    "extract_emails",
    "extract_ats_urls",
    "extract_evidence_snippet",
    "classify_contact_type",
    "classify_execution_route",
    "parse_social_post",
    "run_omni_channel_discovery",
    "run_smart_extract",
    # Bangalore Startup Map
    "fetch_bangalore_map_raw",
    "parse_bangalore_map_rsc",
    "fetch_company_deep_profile",
    "generate_linkedin_connection_note",
    "enrich_startup_website_emails",
    "import_bangalore_startups_to_watchlist",
]
