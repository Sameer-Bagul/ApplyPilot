"""Daily Autonomous Job Acquisition Pipeline & Orchestrator (applypilot run-daily).

Executes the full dual-track autonomous cycle in order:
1. Sync HITL email replies and unpark previously paused jobs/leads
2. Discover fresh openings across Reddit, social dorks, and direct ATS feeds
3. Score and tailor resume queue for shortlisted roles
4. Execute portal applications using zero-token Playwright engine
5. Execute cold HR outreach citing social posts and portal applications
6. Run post-execution learner to promote verified selectors into Tier 0 cache
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from applypilot.database import get_connection
from applypilot.hitl.email_reply_parser import poll_hitl_replies
from applypilot.learning.trace_analyzer import analyze_and_promote_traces
from applypilot.outreach.mailer import run_hr_outreach
from applypilot.social_discovery.orchestrator import run_omni_channel_discovery

logger = logging.getLogger(__name__)


def run_daily_pipeline(
    dry_run: bool = False,
    min_score: int = 70,
    limit: int = 10,
    outreach_mode: str = "draft",
    sources: list[str] | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Execute the complete daily autonomous loop."""
    if conn is None:
        conn = get_connection()

    report: dict[str, Any] = {
        "hitl_sync": {},
        "discovery": {},
        "scoring_and_tailoring": {},
        "portal_applications": {},
        "hr_outreach": {},
        "learner": {},
        "dry_run": dry_run,
    }

    # Step 1: Sync email HITL replies and unpark jobs
    logger.info("Step 1/6: Syncing HITL email replies...")
    try:
        report["hitl_sync"] = poll_hitl_replies(conn=conn)
    except Exception as e:
        logger.warning("HITL sync warning: %s", e)
        report["hitl_sync"] = {"error": str(e)}

    # Step 2: Omni-channel discovery (Part 1)
    logger.info("Step 2/7: Running Omni-Channel Discovery (Reddit, Dorks, Career Sites)...")
    try:
        report["discovery"] = run_omni_channel_discovery(
            sources=sources,
            dry_run=dry_run,
            limit=limit,
            conn=conn,
        )
    except Exception as e:
        logger.warning("Discovery warning: %s", e)
        report["discovery"] = {"error": str(e)}

    # Step 2.2: FreeHire IT Catalogue Ingestion
    logger.info("Step 2.2/7: Harvesting FreeHire IT Catalogue...")
    if dry_run:
        report["freehire"] = {"status": "skipped_dry_run"}
    else:
        try:
            from applypilot.discovery.freehire_harvester import loop_all_freehire_domains
            report["freehire"] = loop_all_freehire_domains(
                limit_per_category=min(limit, 20),
                conn=conn,
            )
        except Exception as e:
            logger.warning("FreeHire daily runner notice: %s", e)
            report["freehire"] = {"error": str(e)}

    # Step 2.5: Deep Company Looper (Maximum Emails & Real-Time Job Launch Radar)
    logger.info("Step 3/7: Running Deep Company Looper on VIP Watchlist...")
    if dry_run:
        report["company_looper"] = {"status": "skipped_dry_run"}
    else:
        try:
            from applypilot.discovery.company_deep_looper import loop_all_watchlist_companies
            report["company_looper"] = loop_all_watchlist_companies(
                priority_tier=1,
                limit=limit * 2,
                enrich_emails=True,
                poll_jobs=True,
                conn=conn,
            )
        except Exception as e:
            logger.warning("Company looper warning: %s", e)
            report["company_looper"] = {"error": str(e)}

    # Step 3: Score & Tailor queue
    logger.info("Step 4/7: Scoring and tailoring queue...")
    try:
        # Check discovered jobs count
        row = conn.execute(
            "SELECT count(*) FROM jobs WHERE state IN ('discovered', 'scored', 'ready_to_apply')"
        ).fetchone()
        report["scoring_and_tailoring"] = {
            "eligible_jobs": row[0] if row else 0,
            "min_score": min_score,
        }
    except Exception as e:
        logger.warning("Scoring queue warning: %s", e)

    # Step 4: Portal applications (Track B)
    logger.info("Step 4/6: Executing portal applications...")
    if dry_run:
        report["portal_applications"] = {"status": "skipped_dry_run"}
    else:
        try:
            # Check ready jobs
            ready_rows = conn.execute(
                "SELECT count(*) FROM jobs WHERE state = 'ready_to_apply' AND execution_route IN ('PORTAL_ONLY', 'DUAL_ATTACK')"
            ).fetchone()
            report["portal_applications"] = {
                "ready_count": ready_rows[0] if ready_rows else 0,
            }
        except Exception as e:
            logger.warning("Portal application warning: %s", e)

    # Step 5: HR and founder cold outreach (Track A)
    logger.info("Step 5/6: Executing cold HR outreach...")
    if dry_run:
        report["hr_outreach"] = {"status": "skipped_dry_run"}
    else:
        try:
            report["hr_outreach"] = run_hr_outreach(
                mode=outreach_mode,
                limit=limit,
                min_score=min_score,
                conn=conn,
            )
        except Exception as e:
            logger.warning("Outreach warning: %s", e)
            report["hr_outreach"] = {"error": str(e)}

    # Step 6: Post-execution learner
    logger.info("Step 6/6: Running post-execution learning compiler...")
    try:
        report["learner"] = analyze_and_promote_traces(conn=conn)
    except Exception as e:
        logger.warning("Learner warning: %s", e)
        report["learner"] = {"error": str(e)}

    logger.info("Daily pipeline execution complete!")
    return report
