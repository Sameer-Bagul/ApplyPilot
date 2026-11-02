"""Facade re-exporting Bangalore Map Harvester from applypilot.discovery."""

from applypilot.discovery.bangalore_map_harvester import (
    check_domain_mx,
    enrich_all_watchlist_companies,
    enrich_startup_emails_deep,
    enrich_startup_website_emails,
    fetch_bangalore_map_raw,
    fetch_company_deep_profile,
    generate_linkedin_connection_note,
    import_bangalore_startups_to_watchlist,
    parse_bangalore_map_rsc,
)

__all__ = [
    "fetch_bangalore_map_raw",
    "parse_bangalore_map_rsc",
    "fetch_company_deep_profile",
    "generate_linkedin_connection_note",
    "enrich_startup_website_emails",
    "check_domain_mx",
    "enrich_startup_emails_deep",
    "enrich_all_watchlist_companies",
    "import_bangalore_startups_to_watchlist",
]
