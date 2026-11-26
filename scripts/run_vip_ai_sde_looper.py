"""VIP AI and SDE Companies Deep Looper (Full Power).

Runs deep looping on full power across the first 100 VIP companies
targeting AI and SDE roles:
1. Normalizes and enriches corporate domains via known overrides and Google DoH MX lookups.
2. Harvests verified deliverable direct inboxes (careers@, talent@, engineering@, founders@)
   and crawls official company leadership/contact sites via cascade harvester.
3. Polls public ATS feeds (Greenhouse, Lever, Ashby, Workday, Workable, SmartRecruiters, BambooHR)
   and parses JSON-LD JobPosting schemas for real-time open AI/SDE positions.
4. Populates recruiter_leads with is_deliverable=1, outreach_status='queued'.
5. Ingests all matching jobs into jobs table with execution_route='DUAL_ATTACK'.
6. Updates career_watchlist with verified counts, ATS tokens, and official domains.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import logging
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
if str(PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from applypilot.career_resolver.ats_feeds import poll_board
from applypilot.career_resolver.jsonld_parser import extract_jsonld_jobpostings
from applypilot.career_resolver.resolver import resolve_company_career_page
from applypilot.database import commit_with_retry, get_connection, store_jobs, store_recruiter_lead
from applypilot.discovery.email_hunter import (
    clean_domain,
    check_domain_mx_provider,
    harvest_company_emails_cascade,
)
from applypilot.discovery.url_normalize import canonicalize_application_url
from applypilot.learning.migrations import _clean_domain_token, is_aggregator_or_ats_domain

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("vip_looper")

DOMAIN_OVERRIDES = {
    "affirm": "affirm.com",
    "ai21 labs": "ai21.com",
    "ai4bharat": "ai4bharat.org",
    "ada": "ada.cx",
    "agentql": "agentql.com",
    "agenta": "agenta.ai",
    "aisdr": "aisdr.com",
    "aider": "aider.chat",
    "aikido security": "aikido.dev",
    "air ai": "air.ai",
    "airbase": "airbase.com",
    "airbyte": "airbyte.com",
    "airtable": "airtable.com",
    "airwallex": "airwallex.com",
    "aisera": "aisera.com",
    "akamai": "akamai.com",
    "anyscale": "anyscale.com",
    "anyword": "anyword.com",
    "apollo ai": "apollo.io",
    "arize ai": "arize.com",
    "arthur ai": "arthur.ai",
    "artisan ai": "artisan.co",
    "assemblyai": "assemblyai.com",
    "autogen": "microsoft.com",
    "aviator": "aviator.co",
    "axiom.ai": "axiom.ai",
    "ayur.ai": "ayur.ai",
    "beacons": "beacons.ai",
    "berriai": "berri.ai",
    "bland ai": "bland.ai",
    "botpress": "botpress.com",
    "chroma": "trychroma.com",
    "civitai": "civitai.com",
    "clari": "clari.com",
    "coloop": "coloop.ai",
    "calmado labs": "calmado.ai",
    "eveoai": "eveo.ai",
    "ideas to impacts innovation": "ideastoimpacts.com",
    "stylabs technologies": "stylabs.in",
    "the strong ai": "thestrong.ai",
    "cellstrat": "cellstrat.com",
    "csb": "csb.co.in",
    "getcrux": "getcrux.ai",
    "icapital": "icapital.com",
    "hemut": "hemut.com",
    "vela": "tryvela.ai",
    "mindtickle": "mindtickle.com",
    "cognition ai": "cognition.ai",
    "cloudflare": "cloudflare.com",
    "datadog": "datadoghq.com",
    "figma": "figma.com",
    "ramp": "ramp.com",
    "sentry": "sentry.io",
    "devrev": "devrev.ai",
    "acceldata": "acceldata.io",
    "dropbox": "dropbox.com",
    "fasal": "fasal.co",
    "aspora": "aspora.com",
    "atlan": "atlan.com",
    "clueso": "clueso.io",
    "stack ai": "stack-ai.com",
    "allegion india": "allegion.com",
}

AI_SDE_KEYWORDS = [
    "engineer", "developer", "ai", "ml", "machine learning", "sde", "software",
    "data", "backend", "frontend", "fullstack", "full stack", "applied scientist",
    "research scientist", "deep learning", "nlp", "llm", "generative ai", "agent",
    "infrastructure", "platform", "systems", "devops", "cloud", "architect",
    "algorithms", "computer vision", "analytics"
]

def is_ai_sde_role(title: str, description: str = "") -> bool:
    """Determine if a job title matches genuine AI, Data, or Software Engineering roles."""
    from run_all_companies_looper import is_ai_sde_role as _is_ai_sde
    return _is_ai_sde(title, description)

def resolve_ats_from_url(url: str | None) -> tuple[str | None, str | None]:
    """Extract ATS provider and board token from URL."""
    from run_all_companies_looper import resolve_ats_from_url as _resolve
    return _resolve(url)


def process_company(company: dict[str, Any], client: httpx.Client | None = None, conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    """Execute complete deep loop on a single VIP company."""
    from run_all_companies_looper import verify_domain_with_http, crawl_custom_careers_page
    if conn is None:
        conn = get_connection()
    c_name = (company.get("company_name") or "").strip()
    if company.get("stage") == "gtm_excluded" or c_name.lower() == "revcloud":
        return {
            "company": c_name,
            "domain": company.get("official_domain"),
            "skipped": "gtm_excluded",
            "mx_valid": False,
            "mx_provider": "none",
            "ats_provider": company.get("ats_provider"),
            "ats_token": company.get("ats_board_token"),
            "emails_added": 0,
            "total_emails": 0,
            "total_jobs_polled": 0,
            "ai_sde_roles_found": 0,
            "new_jobs_stored": 0,
            "sample_ai_sde_roles": [],
        }

    c_domain = _clean_domain_token(company.get("official_domain")) or ""
    if c_domain and is_aggregator_or_ats_domain(c_domain):
        c_domain = ""
    careers_url = company.get("careers_page_url") or ""
    ats_prov = company.get("ats_provider")
    ats_token = company.get("ats_board_token")

    # 1. Resolve verified non-aggregator domain (NO blind {slug}.com guessing)
    c_name_lower = c_name.lower().strip()
    if c_name_lower in DOMAIN_OVERRIDES:
        c_domain = DOMAIN_OVERRIDES[c_name_lower]
    elif not c_domain:
        if careers_url and "://" in careers_url:
            cand = _clean_domain_token(careers_url)
            if cand and "." in cand and not is_aggregator_or_ats_domain(cand):
                c_domain = cand
        if not c_domain:
            try:
                resolved_url = resolve_company_career_page(c_name)
                if resolved_url:
                    cand = _clean_domain_token(resolved_url)
                    if cand and "." in cand and not is_aggregator_or_ats_domain(cand) and verify_domain_with_http(cand, c_name, client=client):
                        c_domain = cand
                        if not careers_url:
                            careers_url = resolved_url
            except Exception:
                pass

    # 2. Check MX Deliverability only on verified non-aggregator domain
    mx_valid, mx_provider = check_domain_mx_provider(c_domain) if (c_domain and not is_aggregator_or_ats_domain(c_domain)) else (False, "none")

    # 3. Harvest Corporate & Decision-Maker Inboxes via Cascade
    existing_leads = conn.execute(
        "SELECT contact_email FROM recruiter_leads WHERE LOWER(company_name) = ? AND contact_email NOT LIKE '%@connect.linkedin.com'",
        (c_name.lower(),),
    ).fetchall()
    existing_emails = {r[0].lower().strip() for r in existing_leads if r[0]}
    emails_added = 0

    if c_domain and len(existing_emails) < 5:
        try:
            h_res = harvest_company_emails_cascade(
                domain=c_domain,
                company_name=c_name,
                limit=6,
                store_to_db=True,
                conn=conn,
            )
            emails_added = h_res.get("leads_stored_to_db", 0)
            existing_leads = conn.execute(
                "SELECT contact_email FROM recruiter_leads WHERE LOWER(company_name) = ? AND contact_email NOT LIKE '%@connect.linkedin.com'",
                (c_name.lower(),),
            ).fetchall()
            existing_emails = {r[0].lower().strip() for r in existing_leads if r[0]}
        except Exception as e:
            logger.debug("Cascade email notice for %s: %s", c_name, e)

    # 4. Resolve ATS Provider and Board Token
    if not ats_prov or not ats_token:
        detected_prov, detected_token = resolve_ats_from_url(careers_url)
        if detected_prov and detected_token:
            ats_prov = detected_prov
            ats_token = detected_token
        elif not ats_prov:
            slug = re.sub(r'[^a-z0-9]', '', c_name_lower)
            for prov in ["greenhouse", "ashby", "lever"]:
                test_jobs = poll_board(prov, slug, client=client)
                if test_jobs:
                    ats_prov = prov
                    ats_token = slug
                    break

    # 5. Poll Open Jobs (ATS or Custom /careers HTML crawl)
    discovered_jobs: list[dict[str, Any]] = []
    if ats_prov and ats_token:
        try:
            discovered_jobs = poll_board(ats_prov, ats_token, client=client)
        except Exception:
            pass
    elif careers_url and "://" in careers_url:
        c_jobs, c_emails, embedded_ats_url = crawl_custom_careers_page(careers_url, c_name, client=client)
        if embedded_ats_url:
            e_prov, e_tok = resolve_ats_from_url(embedded_ats_url)
            if e_prov and e_tok:
                ats_prov, ats_token = e_prov, e_tok
                try:
                    discovered_jobs = poll_board(ats_prov, ats_token, client=client)
                except Exception:
                    pass
        if not discovered_jobs:
            discovered_jobs = c_jobs
        for em in c_emails:
            if em not in existing_emails:
                existing_emails.add(em)
                try:
                    store_recruiter_lead(
                        contact_email=em,
                        role_title=f"Careers Page Contact at {c_name}",
                        company_name=c_name,
                        company_domain=c_domain or em.split("@", 1)[1],
                        contact_name=f"{c_name} Hiring Team",
                        contact_type="recruiter",
                        source_platform="careers_page_scrape",
                        evidence_snippet=f"Extracted directly from {careers_url}",
                        execution_route="DUAL_ATTACK",
                        outreach_status="queued",
                        persona="Talent & Recruiting",
                        conn=conn,
                    )
                    emails_added += 1
                except Exception as e:
                    logger.warning("Failed storing scraped email %s for %s: %s", em, c_name, e)

    # Filter for AI and SDE roles and deduplicate
    ai_sde_jobs = [j for j in discovered_jobs if is_ai_sde_role(j.get("title", ""), j.get("description", ""))]
    new_jobs_stored = 0

    existing_ct = {
        (r[0].strip().lower(), re.sub(r"\s+", " ", r[1].strip().lower()))
        for r in conn.execute(
            "SELECT company, title FROM jobs WHERE LOWER(company) = ? AND title IS NOT NULL",
            (c_name.lower(),),
        ).fetchall()
    }

    has_email = len(existing_emails) > 0
    route = "DUAL_ATTACK" if has_email else "PORTAL_ONLY"

    for j in ai_sde_jobs:
        j_url = j.get("url")
        j_title = j.get("title")
        if not j_url or not j_title:
            continue
        ct_key = (c_name.lower(), re.sub(r"\s+", " ", j_title.strip().lower()))
        if ct_key in existing_ct:
            continue
        existing_ct.add(ct_key)
        try:
            canon_url = canonicalize_application_url(j_url)
            new_cnt, _ = store_jobs(
                conn=conn,
                jobs=[{
                    "url": j_url,
                    "title": j_title,
                    "company": c_name,
                    "location": j.get("location", "Remote / Hybrid"),
                    "description": j.get("description", "")[:1000],
                }],
                site=ats_prov or "vip_deep_looper",
                strategy="vip_deep_looper",
            )
            if new_cnt > 0:
                conn.execute(
                    "UPDATE jobs SET company = COALESCE(company, ?), execution_route = ? WHERE url = ?",
                    (c_name, route, canon_url),
                )
                commit_with_retry(conn)
                new_jobs_stored += 1
        except Exception as e:
            logger.warning("Failed storing job %s for %s: %s", j_url, c_name, e)

    # 6. Update Watchlist Entry safely
    now_iso = datetime.now(timezone.utc).isoformat()
    total_roles = len(discovered_jobs) if discovered_jobs else company.get("open_roles_count", 0)
    safe_domain = c_domain or None
    if safe_domain:
        conflict = conn.execute(
            "SELECT company_id FROM career_watchlist WHERE LOWER(official_domain) = ? AND company_id != ? LIMIT 1",
            (safe_domain.lower(), company["company_id"]),
        ).fetchone()
        if conflict:
            safe_domain = None

    conn.execute(
        """
        UPDATE career_watchlist
        SET official_domain = COALESCE(official_domain, ?),
            careers_page_url = COALESCE(careers_page_url, ?),
            ats_provider = COALESCE(ats_provider, ?),
            ats_board_token = COALESCE(ats_board_token, ?),
            open_roles_count = ?,
            last_checked_at = ?
        WHERE company_id = ?
        """,
        (safe_domain, careers_url or None, ats_prov, ats_token, total_roles, now_iso, company["company_id"]),
    )
    commit_with_retry(conn)

    return {
        "company": c_name,
        "domain": safe_domain or company.get("official_domain"),
        "mx_valid": mx_valid,
        "mx_provider": mx_provider,
        "ats_provider": ats_prov,
        "ats_token": ats_token,
        "emails_added": emails_added,
        "total_emails": len(existing_emails),
        "total_jobs_polled": len(discovered_jobs),
        "ai_sde_roles_found": len(ai_sde_jobs),
        "new_jobs_stored": new_jobs_stored,
        "sample_ai_sde_roles": [j.get("title") for j in ai_sde_jobs[:3]],
    }


def main():
    parser = argparse.ArgumentParser(description="Run deep looper on 100 VIP AI/SDE companies.")
    parser.add_argument("--limit", type=int, default=100, help="Number of VIP companies to process.")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent worker threads.")
    args = parser.parse_args()

    conn = get_connection()
    c = conn.cursor()

    query = """
        SELECT 
            company_id,
            company_name,
            official_domain,
            careers_page_url,
            ats_provider,
            ats_board_token,
            sector,
            priority_tier,
            is_vip,
            open_roles_count
        FROM career_watchlist
        WHERE (is_vip = 1 OR priority_tier = 1)
          AND (stage IS NULL OR stage != 'gtm_excluded')
          AND (
              LOWER(COALESCE(sector, '')) LIKE '%ai%' 
              OR LOWER(COALESCE(sector, '')) LIKE '%llm%'
              OR LOWER(COALESCE(sector, '')) LIKE '%agent%'
              OR LOWER(COALESCE(sector, '')) LIKE '%software%' 
              OR LOWER(COALESCE(sector, '')) LIKE '%developer%' 
              OR LOWER(COALESCE(sector, '')) LIKE '%cloud%' 
              OR LOWER(COALESCE(sector, '')) LIKE '%infrastructure%'
              OR LOWER(COALESCE(sector, '')) LIKE '%engineering%' 
              OR LOWER(COALESCE(sector, '')) LIKE '%data%' 
              OR LOWER(COALESCE(sector, '')) LIKE '%saas%' 
              OR LOWER(company_name) LIKE '%ai%' 
              OR LOWER(company_name) LIKE '%tech%' 
              OR LOWER(company_name) LIKE '%labs%'
          )
          AND NOT (
              LOWER(COALESCE(sector, '')) LIKE '%skincare%' 
              OR LOWER(COALESCE(sector, '')) LIKE '%cleaning%'
              OR LOWER(COALESCE(sector, '')) LIKE '%musculoskeletal%'
          )
        ORDER BY 
            (open_roles_count > 0) DESC,
            open_roles_count DESC,
            company_name ASC
        LIMIT ?
    """

    rows = c.execute(query, (args.limit,)).fetchall()
    companies = [dict(r) for r in rows]
    logger.info("Selected %d VIP AI/SDE companies for full-power deep looping.", len(companies))

    results = []
    total_emails = 0
    total_ai_sde = 0
    total_new_stored = 0

    start_time = time.time()

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json,*/*",
    }
    with httpx.Client(headers=headers, follow_redirects=True, timeout=10.0) as client:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_company = {
                executor.submit(process_company, comp, client): comp for comp in companies
            }
            completed = 0
            for future in concurrent.futures.as_completed(future_to_company):
                comp = future_to_company[future]
                completed += 1
                try:
                    res = future.result()
                    results.append(res)
                    total_emails += res["emails_added"]
                    total_ai_sde += res["ai_sde_roles_found"]
                    total_new_stored += res["new_jobs_stored"]
                    logger.info(
                        "[%d/%d] %s (%s) -> MX: %s (%s) | Emails: +%d (tot: %d) | AI/SDE Roles: %d | New Stored: %d",
                        completed,
                        len(companies),
                        res["company"],
                        res["domain"],
                        "OK" if res["mx_valid"] else "FAIL",
                        res["mx_provider"],
                        res["emails_added"],
                        res["total_emails"],
                        res["ai_sde_roles_found"],
                        res["new_jobs_stored"],
                    )
                except Exception as e:
                    logger.error("[%d/%d] Error processing %s: %s", completed, len(companies), comp.get("company_name"), e)

    duration = time.time() - start_time
    logger.info("=" * 60)
    logger.info("Deep Looper Complete in %.2fs!", duration)
    logger.info("Companies Processed: %d", len(results))
    logger.info("New Deliverable Inboxes Added: %d", total_emails)
    logger.info("Total Live AI/SDE Roles Detected: %d", total_ai_sde)
    logger.info("Brand New Jobs Ingested: %d", total_new_stored)
    logger.info("=" * 60)

    # Save summary report artifact
    data_dir = PROJECT_ROOT / "data-we-can-use"
    data_dir.mkdir(parents=True, exist_ok=True)
    report_path = data_dir / "vip_100_ai_sde_looper_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": round(duration, 2),
                "companies_processed": len(results),
                "total_emails_added": total_emails,
                "total_ai_sde_roles_found": total_ai_sde,
                "total_new_jobs_stored": total_new_stored,
                "companies": results,
            },
            f,
            indent=2,
        )
    logger.info("Summary report saved to %s", report_path)


if __name__ == "__main__":
    main()
