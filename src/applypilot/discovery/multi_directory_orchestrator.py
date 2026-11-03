"""Multi-Directory Omni Harvester & Deep Looping Orchestrator.

Coordinates all high-signal startup maps and directories:
1. Bangalore Startup Map (bangalorestartupmap.com) — 1,085+ startups & 6,400+ jobs
2. Y Combinator Public API (yc-oss/api) — 1,504 hiring startups (India & Remote)
3. TopStartups.io (topstartups.io/jobs) — Newly funded VC-backed startups & ATS links
4. BLR Startup Arena (blrstartuparena.com) — 749 Bangalore tech companies across 42 localities

Runs the unified Deep Looping Engine across all newly ingested and existing watchlist
startups to ensure 5-10 verified emails and all live ATS jobs per company.
"""

from __future__ import annotations

import logging
from typing import Any

from applypilot.database import get_connection
from applypilot.discovery.bangalore_map_harvester import (
    enrich_all_watchlist_companies,
    fetch_bangalore_map_raw,
    ingest_bangalore_map_to_db,
    parse_bangalore_map_rsc,
)
from applypilot.discovery.blr_arena_harvester import (
    fetch_blr_arena_startups,
    ingest_blr_arena_to_db,
)
from applypilot.discovery.startupfundraising_harvester import (
    fetch_startupfundraising_html,
    ingest_fundraising_founders_to_db,
    parse_founders_html,
)
from applypilot.discovery.startupmap_one_harvester import (
    fetch_startupmap_html,
    ingest_startupmap_jobs_to_db,
    parse_startupmap_jobs,
)
from applypilot.discovery.topstartups_harvester import (
    ingest_topstartups_to_db,
    scrape_topstartups_jobs,
)
from applypilot.discovery.vc_portfolio_harvester import (
    fetch_consider_board_jobs,
    fetch_getro_board_jobs,
    ingest_vc_jobs_to_db,
)
from applypilot.discovery.yc_harvester import (
    fetch_yc_startups,
    ingest_yc_startups_to_db,
)

logger = logging.getLogger(__name__)


def run_omni_startup_harvest(
    include_bangalore_map: bool = True,
    include_yc: bool = True,
    include_topstartups: bool = True,
    include_blr_arena: bool = True,
    include_vc_boards: bool = True,
    include_startupfundraising: bool = True,
    include_startupmap_one: bool = True,
    yc_india_only: bool = True,
    yc_remote_only: bool = False,
    topstartups_location: str = "Bangalore",
    topstartups_pages: int = 2,
    limit_per_source: int = 50,
    enrich_emails: bool = True,
    target_emails_per_startup: int = 6,
    conn: Any = None,
) -> dict[str, Any]:
    """Execute omni-directory startup harvest across all high-signal sources.

    Args:
        include_bangalore_map: Ingest from bangalorestartupmap.com
        include_yc: Ingest from YC OSS API
        include_topstartups: Scrape from TopStartups.io
        include_blr_arena: Ingest from blrstartuparena.com
        include_vc_boards: Ingest from Getro (Accel, Khosla, GC, Thrive) & Consider (LSVP)
        include_startupfundraising: Ingest Bengaluru founders with direct LinkedIn links
        include_startupmap_one: Ingest startupmap.one curated startup jobs
        yc_india_only: Filter YC startups to India
        yc_remote_only: Filter YC startups to Remote
        topstartups_location: Location for TopStartups (default 'Bangalore')
        topstartups_pages: Number of pages to scrape from TopStartups
        limit_per_source: Max startups to ingest per directory
        enrich_emails: Whether to trigger deep email synthesis
        target_emails_per_startup: Target verified emails per company
        conn: Optional SQLite connection
    """
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    grand_summary: dict[str, Any] = {
        "bangalore_map": {},
        "yc": {},
        "topstartups": {},
        "blr_arena": {},
        "vc_boards": {},
        "startupfundraising": {},
        "startupmap_one": {},
        "total_startups_ingested": 0,
        "total_jobs_stored": 0,
        "total_leads_created": 0,
        "total_domains_verified": 0,
    }

    try:
        # 1. Bangalore Startup Map
        if include_bangalore_map:
            logger.info("Harvesting Bangalore Startup Map...")
            try:
                html = fetch_bangalore_map_raw()
                startups, roles_dict, kw_dict = parse_bangalore_map_rsc(html)
                if limit_per_source:
                    startups = startups[:limit_per_source]
                bm_stats = ingest_bangalore_map_to_db(
                    startups=startups,
                    roles_by_slug=roles_dict,
                    role_keywords_by_slug=kw_dict,
                    conn=conn,
                    enrich_leads=enrich_emails,
                )
                grand_summary["bangalore_map"] = bm_stats
                grand_summary["total_startups_ingested"] += bm_stats.get("startups_ingested", 0)
                grand_summary["total_jobs_stored"] += bm_stats.get("jobs_stored", 0)
                grand_summary["total_leads_created"] += bm_stats.get("leads_created", 0)
            except Exception as exc:
                logger.error("Bangalore Startup Map harvest failed: %s", exc)
                grand_summary["bangalore_map"] = {"error": str(exc)}

        # 2. Y Combinator OSS API
        if include_yc:
            logger.info("Harvesting Y Combinator Startups...")
            try:
                yc_cos = fetch_yc_startups(
                    india_only=yc_india_only,
                    remote_only=yc_remote_only,
                    hiring_only=True,
                    limit=limit_per_source,
                )
                yc_stats = ingest_yc_startups_to_db(
                    startups=yc_cos,
                    enrich_emails=enrich_emails,
                    target_emails_per_startup=target_emails_per_startup,
                    conn=conn,
                )
                grand_summary["yc"] = yc_stats
                grand_summary["total_startups_ingested"] += yc_stats.get("startups_ingested", 0)
                grand_summary["total_leads_created"] += yc_stats.get("leads_created", 0)
                grand_summary["total_domains_verified"] += yc_stats.get("domains_verified", 0)
            except Exception as exc:
                logger.error("YC harvest failed: %s", exc)
                grand_summary["yc"] = {"error": str(exc)}

        # 3. TopStartups.io
        if include_topstartups:
            logger.info("Harvesting TopStartups.io (%s)...", topstartups_location)
            try:
                ts_jobs = scrape_topstartups_jobs(
                    location=topstartups_location,
                    max_pages=topstartups_pages,
                )
                ts_stats = ingest_topstartups_to_db(
                    jobs_data=ts_jobs,
                    enrich_emails=enrich_emails,
                    target_emails_per_startup=target_emails_per_startup,
                    conn=conn,
                )
                grand_summary["topstartups"] = ts_stats
                grand_summary["total_startups_ingested"] += ts_stats.get("companies_ingested", 0)
                grand_summary["total_jobs_stored"] += ts_stats.get("jobs_stored", 0)
                grand_summary["total_leads_created"] += ts_stats.get("leads_created", 0)
                grand_summary["total_domains_verified"] += ts_stats.get("domains_verified", 0)
            except Exception as exc:
                logger.error("TopStartups harvest failed: %s", exc)
                grand_summary["topstartups"] = {"error": str(exc)}

        # 4. BLR Startup Arena
        if include_blr_arena:
            logger.info("Harvesting BLR Startup Arena...")
            try:
                blr_cos = fetch_blr_arena_startups(limit=limit_per_source)
                blr_stats = ingest_blr_arena_to_db(
                    startups=blr_cos,
                    enrich_emails=enrich_emails,
                    target_emails_per_startup=target_emails_per_startup,
                    conn=conn,
                )
                grand_summary["blr_arena"] = blr_stats
                grand_summary["total_startups_ingested"] += blr_stats.get("startups_ingested", 0)
                grand_summary["total_leads_created"] += blr_stats.get("leads_created", 0)
                grand_summary["total_domains_verified"] += blr_stats.get("domains_verified", 0)
            except Exception as exc:
                logger.error("BLR Startup Arena harvest failed: %s", exc)
                grand_summary["blr_arena"] = {"error": str(exc)}

        # 5. VC Portfolio Boards (Getro & Consider)
        if include_vc_boards:
            logger.info("Harvesting VC Portfolio Boards (Accel, Khosla, LSVP)...")
            try:
                accel_jobs = fetch_getro_board_jobs("accel", max_pages=1, hits_per_page=limit_per_source)
                lsvp_jobs = fetch_consider_board_jobs("lightspeed")
                all_vc_jobs = (accel_jobs + lsvp_jobs)[:limit_per_source]
                vc_stats = ingest_vc_jobs_to_db(
                    jobs_data=all_vc_jobs,
                    vc_source="Accel & Lightspeed Portfolio",
                    enrich_emails=enrich_emails,
                    target_emails_per_startup=target_emails_per_startup,
                    conn=conn,
                )
                grand_summary["vc_boards"] = vc_stats
                grand_summary["total_startups_ingested"] += vc_stats.get("companies_ingested", 0)
                grand_summary["total_jobs_stored"] += vc_stats.get("jobs_stored", 0)
                grand_summary["total_leads_created"] += vc_stats.get("leads_created", 0)
                grand_summary["total_domains_verified"] += vc_stats.get("domains_verified", 0)
            except Exception as exc:
                logger.error("VC Portfolio harvest failed: %s", exc)
                grand_summary["vc_boards"] = {"error": str(exc)}

        # 6. StartupFundraising Bengaluru Founders
        if include_startupfundraising:
            logger.info("Harvesting StartupFundraising Bengaluru Founders...")
            try:
                sf_html = fetch_startupfundraising_html()
                founders = parse_founders_html(sf_html)
                if limit_per_source:
                    founders = founders[:limit_per_source]
                sf_stats = ingest_fundraising_founders_to_db(
                    founders=founders,
                    enrich_emails=enrich_emails,
                    target_emails_per_startup=target_emails_per_startup,
                    conn=conn,
                )
                grand_summary["startupfundraising"] = sf_stats
                grand_summary["total_startups_ingested"] += sf_stats.get("companies_ingested", 0)
                grand_summary["total_leads_created"] += sf_stats.get("leads_created", 0)
            except Exception as exc:
                logger.error("StartupFundraising harvest failed: %s", exc)
                grand_summary["startupfundraising"] = {"error": str(exc)}

        # 7. StartupMap.one
        if include_startupmap_one:
            logger.info("Harvesting StartupMap.one jobs...")
            try:
                sm_html = fetch_startupmap_html()
                sm_jobs = parse_startupmap_jobs(sm_html)
                if limit_per_source:
                    sm_jobs = sm_jobs[:limit_per_source]
                sm_stats = ingest_startupmap_jobs_to_db(
                    jobs=sm_jobs,
                    enrich_emails=enrich_emails,
                    target_emails_per_startup=target_emails_per_startup,
                    conn=conn,
                )
                grand_summary["startupmap_one"] = sm_stats
                grand_summary["total_startups_ingested"] += sm_stats.get("companies_ingested", 0)
                grand_summary["total_jobs_stored"] += sm_stats.get("jobs_stored", 0)
            except Exception as exc:
                logger.error("StartupMap.one harvest failed: %s", exc)
                grand_summary["startupmap_one"] = {"error": str(exc)}

        conn.commit()
    finally:
        if should_close:
            conn.close()

    logger.info("Omni Startup Harvest complete: %s", grand_summary)
    return grand_summary


def loop_and_enrich_watchlist(
    limit: int = 50,
    min_emails: int = 5,
    target_count: int = 8,
    conn: Any = None,
) -> dict[str, int]:
    """Execute the deep email enrichment looper across all watchlist companies."""
    return enrich_all_watchlist_companies(
        conn=conn,
        limit=limit,
        min_emails=min_emails,
        target_count=target_count,
    )
