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

from applypilot.career_resolver.ats_feeds import poll_board
from applypilot.career_resolver.jsonld_parser import extract_jsonld_jobpostings
from applypilot.database import get_connection, store_jobs, store_recruiter_lead
from applypilot.discovery.email_hunter import (
    clean_domain,
    check_domain_mx_provider,
    harvest_company_emails_cascade,
)

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
    "bolt ai": "bolt.earth",
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
    """Determine if a job title or description matches AI or SDE roles."""
    text = f"{title} {description[:300]}".lower()
    return any(kw in text for kw in AI_SDE_KEYWORDS)

def resolve_ats_from_url(url: str | None) -> tuple[str | None, str | None]:
    """Extract ATS provider and board token from URL."""
    if not url:
        return None, None
    url_str = url.strip()
    if "greenhouse.io" in url_str:
        m = re.search(r'greenhouse\.io/([^/?#]+)', url_str)
        return "greenhouse", m.group(1) if m else None
    elif "lever.co" in url_str:
        m = re.search(r'lever\.co/([^/?#]+)', url_str)
        return "lever", m.group(1) if m else None
    elif "ashbyhq.com" in url_str:
        m = re.search(r'ashbyhq\.com/([^/?#]+)', url_str)
        return "ashby", m.group(1) if m else None
    elif "workable.com" in url_str:
        m = re.search(r'apply\.workable\.com/([^/?#]+)', url_str)
        return "workable", m.group(1) if m else None
    elif "smartrecruiters.com" in url_str:
        m = re.search(r'smartrecruiters\.com/([^/?#]+)', url_str)
        return "smartrecruiters", m.group(1) if m else None
    elif "bamboohr.com" in url_str:
        m = re.search(r'([^./]+)\.bamboohr\.com', url_str)
        return "bamboohr", m.group(1) if m else None
    elif "myworkdayjobs.com" in url_str:
        parsed = urlparse(url_str)
        host = parsed.netloc
        tenant = host.split(".")[0]
        return "workday", f"{host}/{tenant}/External"
    return None, None

def process_company(company: dict[str, Any], client: httpx.Client | None = None) -> dict[str, Any]:
    """Execute complete deep loop on a single VIP company."""
    conn = get_connection()
    c_name = company.get("company_name", "").strip()
    c_domain = company.get("official_domain") or ""
    careers_url = company.get("careers_page_url") or ""
    ats_prov = company.get("ats_provider")
    ats_token = company.get("ats_board_token")

    # 1. Normalize domain
    c_name_lower = c_name.lower().strip()
    if c_name_lower in DOMAIN_OVERRIDES:
        c_domain = DOMAIN_OVERRIDES[c_name_lower]
    elif not c_domain or any(p in c_domain for p in ["wellfound", "cutshort", "linkedin", "naukri", "ycombinator"]):
        if careers_url and "://" in careers_url:
            parsed = urlparse(careers_url)
            netloc = parsed.netloc.lower().replace("www.", "")
            if not any(ats in netloc for ats in ["greenhouse.io", "ashbyhq.com", "lever.co", "myworkdayjobs.com", "smartrecruiters.com", "wellfound.com", "cutshort.io"]):
                c_domain = netloc
        if not c_domain:
            clean_slug = re.sub(r'[^a-z0-9]', '', c_name_lower)
            c_domain = f"{clean_slug}.com"

    # 2. Check MX Deliverability
    mx_valid, mx_provider = check_domain_mx_provider(c_domain)

    # 3. Harvest Corporate & Decision-Maker Inboxes via Cascade
    existing_leads = conn.execute(
        "SELECT contact_email FROM recruiter_leads WHERE LOWER(company_name) = ? AND contact_email NOT LIKE '%@connect.linkedin.com'",
        (c_name.lower(),),
    ).fetchall()
    existing_emails = {r[0] for r in existing_leads}
    emails_added = 0

    if len(existing_emails) < 5:
        try:
            h_res = harvest_company_emails_cascade(
                domain=c_domain,
                company_name=c_name,
                limit=6,
                store_to_db=True,
                conn=conn,
            )
            emails_added = h_res.get("leads_stored_to_db", 0)
            # Refresh existing emails
            existing_leads = conn.execute(
                "SELECT contact_email FROM recruiter_leads WHERE LOWER(company_name) = ? AND contact_email NOT LIKE '%@connect.linkedin.com'",
                (c_name.lower(),),
            ).fetchall()
            existing_emails = {r[0] for r in existing_leads}
        except Exception as e:
            logger.debug("Cascade email notice for %s: %s", c_name, e)

    # 4. Resolve ATS Provider and Board Token
    if not ats_prov or not ats_token:
        detected_prov, detected_token = resolve_ats_from_url(careers_url)
        if detected_prov and detected_token:
            ats_prov = detected_prov
            ats_token = detected_token
        elif not ats_prov:
            # Try guessing common ATS tokens
            slug = re.sub(r'[^a-z0-9]', '', c_name_lower)
            for prov in ["greenhouse", "ashby", "lever"]:
                test_jobs = poll_board(prov, slug, client=client)
                if test_jobs:
                    ats_prov = prov
                    ats_token = slug
                    break

    # 5. Poll Open Jobs (ATS or JSON-LD parsing)
    discovered_jobs: list[dict[str, Any]] = []
    if ats_prov and ats_token:
        try:
            discovered_jobs = poll_board(ats_prov, ats_token, client=client)
        except Exception:
            pass
    elif careers_url and "://" in careers_url:
        try:
            resp = client.get(careers_url, timeout=6.0) if client else None
            if resp and resp.status_code == 200:
                discovered_jobs = extract_jsonld_jobpostings(resp.text, base_url=careers_url)
        except Exception:
            pass

    # Filter for AI and SDE roles
    ai_sde_jobs = [j for j in discovered_jobs if is_ai_sde_role(j.get("title", ""), j.get("description", ""))]
    new_jobs_stored = 0

    has_email = len(existing_emails) > 0
    route = "DUAL_ATTACK" if has_email else "PORTAL_ONLY"

    for j in ai_sde_jobs:
        j_url = j.get("url")
        j_title = j.get("title")
        if not j_url or not j_title:
            continue
        try:
            new_cnt, _ = store_jobs(
                conn=conn,
                jobs=[{
                    "url": j_url,
                    "title": j_title,
                    "location": j.get("location", "Remote / Hybrid"),
                    "description": j.get("description", "")[:1000],
                }],
                site=ats_prov or "vip_deep_looper",
                strategy="vip_deep_looper",
            )
            conn.execute(
                "UPDATE jobs SET company = ?, execution_route = ? WHERE url = ?",
                (c_name, route, j_url),
            )
            conn.commit()
            if new_cnt > 0:
                new_jobs_stored += 1
        except Exception:
            pass

    # 6. Update Watchlist Entry
    now_iso = datetime.now(timezone.utc).isoformat()
    total_roles = len(discovered_jobs) if discovered_jobs else company.get("open_roles_count", 0)
    conn.execute(
        """
        UPDATE career_watchlist
        SET official_domain = ?,
            ats_provider = COALESCE(ats_provider, ?),
            ats_board_token = COALESCE(ats_board_token, ?),
            open_roles_count = ?,
            last_checked_at = ?
        WHERE company_id = ?
        """,
        (c_domain, ats_prov, ats_token, total_roles, now_iso, company["company_id"]),
    )
    conn.commit()

    return {
        "company": c_name,
        "domain": c_domain,
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
    report_path = Path("/home/sameer/Projects/ApplyPilot/data-we-can-use/vip_100_ai_sde_looper_report.json")
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
