"""Facade re-exporting Bangalore Map Harvester from applypilot.discovery."""

from applypilot.discovery.bangalore_map_harvester import (
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
    "import_bangalore_startups_to_watchlist",
]
