"""Deep Company Looper & Real-Time Job Launch Radar.

Systematically loops through companies in career_watchlist to:
1. Maximize verified emails (5-15 emails per company) via web crawling, founder
   permutations, and Google DoH MX validation.
2. Monitor company career pages and 11 ATS feeds in real-time, detecting brand new
   job openings the moment they launch via ETag, content hashes, and ATS APIs.
3. Automatically link discovered emails and open jobs, assigning execution_route
   (DUAL_ATTACK, EMAIL_ONLY, PORTAL_ONLY) and populating recruiter_leads.
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from applypilot.career_resolver.ats_feeds import poll_board
from applypilot.career_resolver.jsonld_parser import (
    check_page_change,
    extract_jsonld_jobpostings,
)
from applypilot.database import (
    get_connection,
    store_jobs,
    store_recruiter_lead,
)
from applypilot.discovery.bangalore_map_harvester import (
    check_domain_mx,
    enrich_startup_emails_deep,
    generate_linkedin_connection_note,
)
from applypilot.discovery.web_and_social_recruiter_harvester import (
    clean_watchlist_domains,
    enrich_company_deep,
)

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/json,*/*",
}


def loop_and_enrich_single_company(
    company: dict[str, Any],
    enrich_emails: bool = True,
    poll_jobs: bool = True,
    target_emails: int = 8,
    cities: list[str] | None = None,
    client: httpx.Client | None = None,
    conn: Any = None,
) -> dict[str, Any]:
    """Execute deep looping on a single company: maximum emails + real-time job detection."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    c_name = company.get("company_name", "").strip()
    c_domain = company.get("official_domain")
    careers_url = company.get("careers_page_url")
    ats_provider = company.get("ats_provider")
    ats_token = company.get("ats_board_token")
    last_hash = company.get("last_content_hash")

    res = {
        "company": c_name,
        "domain": c_domain,
        "emails_added": 0,
        "total_emails": 0,
        "new_jobs_found": 0,
        "total_jobs": 0,
        "ats_provider": ats_provider,
    }

    if not c_domain and careers_url:
        try:
            parsed = urlparse(careers_url)
            if not any(ats in parsed.netloc for ats in ["greenhouse.io", "lever.co", "ashbyhq.com", "workday"]):
                c_domain = parsed.netloc.lower().replace("www.", "")
        except Exception:
            pass

    # Step 1: Maximum Email Synthesis & Enrichment
    stored_emails = []
    if enrich_emails and (c_domain or careers_url):
        # Check existing emails
        existing = conn.execute(
            "SELECT contact_email FROM recruiter_leads WHERE company_name = ? AND contact_email NOT LIKE '%@connect.linkedin.com'",
            (c_name,),
        ).fetchall()
        existing_emails = {r[0] for r in existing}

        f_names = []
        f_raw = company.get("founders_json")
        f_linkedins = []
        if f_raw:
            try:
                parsed_f = json.loads(f_raw)
                f_names = parsed_f.get("names") or []
                f_linkedins = parsed_f.get("linkedin_urls") or []
            except Exception:
                pass

        if len(existing_emails) < target_emails:
            deep_res = enrich_company_deep(
                company_name=c_name,
                domain=c_domain,
                careers_page_url=careers_url,
                target_count=target_emails,
                cities=cities,
                conn=conn,
            )
            added = deep_res.get("new_leads_added", 0)
            if added == 0 and c_domain:
                try:
                    from applypilot.discovery.email_hunter import harvest_company_emails_cascade
                    h_res = harvest_company_emails_cascade(
                        domain=c_domain,
                        company_name=c_name,
                        limit=target_emails,
                        store_to_db=True,
                        conn=conn,
                    )
                    added = h_res.get("leads_stored_to_db", 0)
                except Exception as e:
                    logger.debug("Cascade email harvest notice: %s", e)
            res["emails_added"] += added
            res["total_emails"] = len(existing_emails) + added

    # Step 2: Real-Time Job Launch Radar
    discovered_jobs: list[dict[str, Any]] = []
    new_content_hash = last_hash

    if poll_jobs:
        # A. If known ATS provider and board token
        if ats_provider and ats_token:
            discovered_jobs = poll_board(ats_provider, ats_token, client=client)
        # B. If ATS URL in careers_page_url
        elif careers_url:
            matched_ats = None
            token = None
            if "greenhouse.io" in careers_url:
                matched_ats = "greenhouse"
                m = re.search(r'greenhouse\.io/([^/?#]+)', careers_url)
                token = m.group(1) if m else None
            elif "lever.co" in careers_url:
                matched_ats = "lever"
                m = re.search(r'lever\.co/([^/?#]+)', careers_url)
                token = m.group(1) if m else None
            elif "ashbyhq.com" in careers_url:
                matched_ats = "ashby"
                m = re.search(r'ashbyhq\.com/([^/?#]+)', careers_url)
                token = m.group(1) if m else None

            if matched_ats and token:
                discovered_jobs = poll_board(matched_ats, token, client=client)
                res["ats_provider"] = matched_ats
            else:
                # Custom careers page: check ETag / Content Hash & parse JSON-LD
                changed, n_hash, _, html = check_page_change(
                    url=careers_url,
                    last_hash=last_hash,
                    client=client,
                )
                if changed and html:
                    new_content_hash = n_hash
                    discovered_jobs = extract_jsonld_jobpostings(html, base_url=careers_url)

        # Ingest discovered jobs and detect brand new openings
        for j in discovered_jobs:
            j_url = j.get("url")
            j_title = j.get("title") or f"Open Role at {c_name}"
            if not j_url:
                continue

            has_email = res["total_emails"] > 0
            route = "DUAL_ATTACK" if has_email else "PORTAL_ONLY"

            try:
                new_cnt, _ = store_jobs(
                    conn=conn,
                    jobs=[{
                        "url": j_url,
                        "title": j_title,
                        "location": j.get("location", "Remote"),
                        "description": j.get("description", ""),
                    }],
                    site=j.get("site") or "company_looper",
                    strategy="company_deep_looper",
                )
                conn.execute(
                    "UPDATE jobs SET company = ?, execution_route = ? WHERE url = ?",
                    (c_name, route, j_url),
                )
                conn.commit()
                if new_cnt > 0:
                    res["new_jobs_found"] += 1
            except Exception:
                pass

        res["total_jobs"] = len(discovered_jobs)

        # Update watchlist record
        now_iso = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            UPDATE career_watchlist
            SET open_roles_count = ?, last_checked_at = ?, last_content_hash = ?,
                official_domain = COALESCE(official_domain, ?),
                ats_provider = COALESCE(ats_provider, ?)
            WHERE company_name = ?
            """,
            (
                res["total_jobs"],
                now_iso,
                new_content_hash,
                c_domain,
                res.get("ats_provider"),
                c_name,
            ),
        )
        conn.commit()

    if should_close:
        conn.close()

    return res


def loop_all_watchlist_companies(
    priority_tier: int | None = 1,
    vip_only: bool = False,
    limit: int = 50,
    target_emails: int = 8,
    enrich_emails: bool = True,
    poll_jobs: bool = True,
    cities: list[str] | None = None,
    conn: Any = None,
) -> dict[str, Any]:
    """Loop over all companies in career_watchlist to maximize emails and capture open jobs."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    # Clean and normalize any malformed domains in watchlist
    clean_watchlist_domains(conn=conn)

    query = """
        SELECT *,
               (SELECT COUNT(*) FROM recruiter_leads r WHERE LOWER(r.company_name) = LOWER(career_watchlist.company_name)) AS current_leads_count
        FROM career_watchlist WHERE 1=1
    """
    params: list[Any] = []
    if vip_only:
        query += " AND is_vip = 1"
    if priority_tier is not None:
        query += " AND priority_tier <= ?"
        params.append(priority_tier)

    query += " ORDER BY current_leads_count ASC, is_vip DESC, priority_tier ASC, last_checked_at ASC NULLS FIRST LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    companies = [dict(r) for r in rows]

    summary = {
        "companies_processed": len(companies),
        "total_emails_added": 0,
        "total_new_jobs_found": 0,
        "companies_with_new_jobs": 0,
        "results": [],
    }

    with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=10.0) as client:
        for c in companies:
            c_res = loop_and_enrich_single_company(
                company=c,
                enrich_emails=enrich_emails,
                poll_jobs=poll_jobs,
                target_emails=target_emails,
                cities=cities,
                client=client,
                conn=conn,
            )
            summary["total_emails_added"] += c_res["emails_added"]
            summary["total_new_jobs_found"] += c_res["new_jobs_found"]
            if c_res["new_jobs_found"] > 0:
                summary["companies_with_new_jobs"] += 1
            summary["results"].append(c_res)

    if should_close:
        conn.close()

    logger.info("Deep Looper completed for %d companies: %d new jobs, %d emails added",
                len(companies), summary["total_new_jobs_found"], summary["total_emails_added"])
    return summary


def run_continuous_watch(
    interval_seconds: int = 21600,  # 6 hours default
    priority_tier: int = 1,
    limit_per_sweep: int = 100,
    conn: Any = None,
) -> None:
    """Run continuous background sweeper to detect freshly launched jobs and enrich emails."""
    logger.info("Starting continuous company watch loop (interval: %ds)...", interval_seconds)
    while True:
        try:
            summary = loop_all_watchlist_companies(
                priority_tier=priority_tier,
                limit=limit_per_sweep,
                conn=conn,
            )
            logger.info("Watch sweep completed: %s", summary)
        except Exception as e:
            logger.error("Error in continuous watch loop: %s", e)
        time.sleep(interval_seconds)

