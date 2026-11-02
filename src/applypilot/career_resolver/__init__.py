"""Part 1B: Direct Company Career Feeds & ATS Resolver module (Facade).

Unified implementation resides in applypilot.discovery.
This module maintains 100% backward compatibility for all existing imports.
"""

from applypilot.discovery import (
    bootstrap_from_open_apply_jobs,
    extract_ats_from_page,
    extract_jobpostings_from_html,
    extract_slug_from_ats_url,
    get_latest_common_crawl_index,
    harvest_common_crawl_slugs,
    harvest_crtsh_career_subdomains,
    harvest_sitemap_career_urls,
    poll_ashby_board,
    poll_board,
    poll_greenhouse_board,
    poll_lever_board,
    poll_watchlist,
    read_open_apply_parquet,
    resolve_company_ats,
    resolve_company_career_page,
    sync_slugs_to_watchlist,
    unshorten_url,
)

__all__ = [
    "poll_greenhouse_board",
    "poll_lever_board",
    "poll_ashby_board",
    "poll_board",
    "poll_watchlist",
    "unshorten_url",
    "resolve_company_career_page",
    "extract_ats_from_page",
    "resolve_company_ats",
    "extract_jobpostings_from_html",
    "extract_slug_from_ats_url",
    "get_latest_common_crawl_index",
    "harvest_common_crawl_slugs",
    "harvest_crtsh_career_subdomains",
    "harvest_sitemap_career_urls",
    "bootstrap_from_open_apply_jobs",
    "read_open_apply_parquet",
    "sync_slugs_to_watchlist",
]
