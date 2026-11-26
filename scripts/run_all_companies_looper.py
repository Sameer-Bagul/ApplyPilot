"""All Companies Deep Looper (Industrial High-Throughput & Optimized).

Loops systematically across all targetable companies in career_watchlist:
1. Normalizes domains and verifies MX deliverability via Google DoH.
2. Synthesizes deliverable direct corporate inboxes (careers@, talent@, engineering@, founders@)
   for all MX-verified domains.
3. Selectively probes ATS APIs (Greenhouse, Lever, Ashby, Workable, SmartRecruiters, BambooHR, Workday)
   for tech/engineering/VIP companies, saving network roundtrips on non-tech firms.
4. Populates recruiter_leads with is_deliverable=1, outreach_status='queued'.
5. Links active engineering/AI jobs into jobs table with execution_route='DUAL_ATTACK'.
6. Updates career_watchlist with verified counts and ATS details.
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
from datetime import datetime, timezone, timedelta
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
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("all_looper")

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

TECH_SECTORS = [
    "ai", "software", "tech", "cloud", "saas", "developer", "data", "engineering",
    "it", "fintech", "healthtech", "deeptech", "edtech", "ecommerce", "internet"
]

_MX_CACHE: dict[str, tuple[bool, str]] = {}


def get_cached_mx(domain: str) -> tuple[bool, str]:
    """Check MX with in-memory caching for speed."""
    clean_d = clean_domain(domain)
    if not clean_d or "." not in clean_d:
        return False, "none"
    if clean_d in _MX_CACHE:
        return _MX_CACHE[clean_d]
    valid, provider = check_domain_mx_provider(clean_d, timeout=3.0)
    _MX_CACHE[clean_d] = (valid, provider)
    return valid, provider


def is_ai_sde_role(title: str, description: str = "") -> bool:
    """Determine if a job title or description matches AI or SDE roles."""
    text = f"{title} {description[:300]}".lower()
    return any(kw in text for kw in AI_SDE_KEYWORDS)


def is_tech_company(company: dict[str, Any]) -> bool:
    """Determine if company is tech/software/AI focused."""
    if company.get("is_vip") == 1 or company.get("priority_tier") == 1:
        return True
    sector = (company.get("sector") or "").lower()
    c_name = (company.get("company_name") or "").lower()
    return any(ts in sector for ts in TECH_SECTORS) or any(ts in c_name for ts in ["ai", "tech", "soft", "labs", "data"])


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


def process_single_company(company: dict[str, Any], client: httpx.Client | None = None) -> dict[str, Any]:
    """Execute complete deep loop on a single company."""
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
    elif not c_domain or any(p in c_domain for p in ["wellfound", "cutshort", "linkedin", "naukri", "ycombinator", "indeed"]):
        if careers_url and "://" in careers_url:
            parsed = urlparse(careers_url)
            netloc = parsed.netloc.lower().replace("www.", "")
            if not any(ats in netloc for ats in ["greenhouse.io", "ashbyhq.com", "lever.co", "myworkdayjobs.com", "smartrecruiters.com", "wellfound.com", "cutshort.io"]):
                c_domain = netloc
        if not c_domain:
            clean_slug = re.sub(r'[^a-z0-9]', '', c_name_lower)
            if clean_slug:
                c_domain = f"{clean_slug}.com"

    # 2. Check MX Deliverability
    mx_valid, mx_provider = get_cached_mx(c_domain)

    # 3. Harvest Corporate & Decision-Maker Inboxes
    existing_leads = conn.execute(
        "SELECT contact_email FROM recruiter_leads WHERE LOWER(company_name) = ? AND contact_email NOT LIKE '%@connect.linkedin.com'",
        (c_name.lower(),),
    ).fetchall()
    existing_emails = {r[0] for r in existing_leads}
    emails_added = 0

    if mx_valid and len(existing_emails) < 5:
        standard_prefixes = [
            ("careers", "Head of Talent / Recruiting", "recruiter", 0.95),
            ("talent", "Talent Acquisition Lead", "recruiter", 0.94),
            ("hiring", "Technical Hiring Manager", "hiring_manager", 0.92),
            ("engineering", "VP of Engineering / Tech Lead", "hiring_manager", 0.88),
            ("founders", "Founding Team", "founder", 0.85),
        ]
        for prefix, role, c_type, conf in standard_prefixes:
            em = f"{prefix}@{c_domain}".lower()
            if em not in existing_emails:
                existing_emails.add(em)
                try:
                    store_recruiter_lead(
                        conn=conn,
                        lead_data={
                            "company_name": c_name,
                            "company_domain": c_domain,
                            "contact_name": f"{c_name} {role}",
                            "role_title": f"{role} at {c_name}",
                            "contact_email": em,
                            "contact_type": c_type,
                            "source_platform": f"mx_verified_{mx_provider}",
                            "evidence_snippet": f"Verified corporate mail exchanger ({mx_provider}) with active MX route",
                            "execution_route": "DUAL_ATTACK",
                            "outreach_status": "queued",
                            "is_deliverable": 1,
                            "mx_provider": mx_provider,
                            "persona": "Engineering Leadership" if "Engineering" in role else "Talent & Recruiting",
                            "priority_score": 85,
                        },
                    )
                    emails_added += 1
                except Exception:
                    pass

    # 4. Resolve ATS Provider and Board Token
    is_tech = is_tech_company(company)
    if not ats_prov or not ats_token:
        detected_prov, detected_token = resolve_ats_from_url(careers_url)
        if detected_prov and detected_token:
            ats_prov = detected_prov
            ats_token = detected_token
        elif not ats_prov and is_tech and len(c_name_lower) >= 3:
            slug = re.sub(r'[^a-z0-9]', '', c_name_lower)
            for prov in ["greenhouse", "ashby", "lever"]:
                try:
                    test_jobs = poll_board(prov, slug, client=client)
                    if test_jobs:
                        ats_prov = prov
                        ats_token = slug
                        break
                except Exception:
                    pass

    # 5. Poll Open Jobs (ATS or JSON-LD parsing)
    discovered_jobs: list[dict[str, Any]] = []
    if ats_prov and ats_token:
        try:
            discovered_jobs = poll_board(ats_prov, ats_token, client=client)
        except Exception:
            pass
    elif is_tech and careers_url and "://" in careers_url:
        try:
            resp = client.get(careers_url, timeout=4.0) if client else None
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
                site=ats_prov or "company_looper",
                strategy="all_companies_looper",
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
    }


def main():
    parser = argparse.ArgumentParser(description="Run deep looper on all companies.")
    parser.add_argument("--tier", type=int, default=None, help="Filter by priority tier (1, 2, 3).")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of companies.")
    parser.add_argument("--workers", type=int, default=16, help="Concurrent worker threads.")
    parser.add_argument("--minutes-ago", type=int, default=30, help="Skip companies checked within past N minutes.")
    args = parser.parse_args()

    conn = get_connection()
    c = conn.cursor()

    cutoff_iso = (datetime.now(timezone.utc) - timedelta(minutes=args.minutes_ago)).isoformat()

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
            open_roles_count,
            referral_available,
            last_checked_at
        FROM career_watchlist
        WHERE (stage IS NULL OR stage != 'gtm_excluded')
          AND (last_checked_at IS NULL OR last_checked_at < ?)
    """
    params: list[Any] = [cutoff_iso]

    if args.tier is not None:
        query += " AND priority_tier = ?"
        params.append(args.tier)

    # Order by VIP first, then priority_tier, then whether they have referrals or open roles
    query += """
        ORDER BY 
            is_vip DESC,
            priority_tier ASC,
            referral_available DESC,
            (open_roles_count > 0) DESC,
            open_roles_count DESC,
            company_name ASC
    """

    if args.limit:
        query += " LIMIT ?"
        params.append(args.limit)

    rows = c.execute(query, params).fetchall()
    filtered = [dict(r) for r in rows]

    logger.info("Starting All-Companies Deep Looper: %d companies queued for processing with %d worker threads.",
                len(filtered), args.workers)

    results = []
    total_emails = 0
    total_ai_sde = 0
    total_new_stored = 0
    start_time = time.time()

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json,*/*",
    }
    limits = httpx.Limits(max_keepalive_connections=50, max_connections=100)
    with httpx.Client(headers=headers, limits=limits, follow_redirects=True, timeout=5.0) as client:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_comp = {
                executor.submit(process_single_company, comp, client): comp for comp in filtered
            }
            completed = 0

            for future in concurrent.futures.as_completed(future_to_comp):
                comp = future_to_comp[future]
                completed += 1
                try:
                    res = future.result()
                    results.append(res)
                    total_emails += res["emails_added"]
                    total_ai_sde += res["ai_sde_roles_found"]
                    total_new_stored += res["new_jobs_stored"]

                    if completed % 50 == 0 or completed == len(filtered):
                        elapsed = time.time() - start_time
                        rate = completed / elapsed if elapsed > 0 else 0
                        eta = (len(filtered) - completed) / rate if rate > 0 else 0
                        logger.info(
                            "Progress: [%d/%d] (%.1f%%) | Rate: %.1f comp/s | ETA: %.0fs (%.1fm) | Emails: +%d | Roles: %d | New Jobs: %d",
                            completed,
                            len(filtered),
                            (completed / len(filtered)) * 100,
                            rate,
                            eta,
                            eta / 60,
                            total_emails,
                            total_ai_sde,
                            total_new_stored,
                        )

                    # Save progress checkpoint every 250 companies
                    if completed % 250 == 0:
                        cp_path = Path("/home/sameer/Projects/ApplyPilot/data-we-can-use/all_companies_looper_progress.json")
                        with open(cp_path, "w", encoding="utf-8") as f:
                            json.dump({
                                "completed": completed,
                                "total": len(filtered),
                                "emails_added": total_emails,
                                "ai_sde_roles": total_ai_sde,
                                "new_jobs": total_new_stored,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }, f)

                except Exception as e:
                    logger.error("[%d/%d] Error processing %s: %s", completed, len(filtered), comp.get("company_name"), e)

    duration = time.time() - start_time
    logger.info("=" * 65)
    logger.info("ALL COMPANIES DEEP LOOPER COMPLETE in %.1fs (%.1f min)!", duration, duration / 60)
    logger.info("Total Companies Processed: %d", len(results))
    logger.info("Total Deliverable Inboxes Added: %d", total_emails)
    logger.info("Total Live AI/SDE Roles Detected: %d", total_ai_sde)
    logger.info("Brand New Jobs Ingested: %d", total_new_stored)
    logger.info("=" * 65)

    # Save final report
    final_report_path = Path("/home/sameer/Projects/ApplyPilot/data-we-can-use/all_companies_looper_final_report.json")
    with open(final_report_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": round(duration, 2),
            "companies_processed": len(results),
            "total_emails_added": total_emails,
            "total_ai_sde_roles_found": total_ai_sde,
            "total_new_jobs_stored": total_new_stored,
        }, f, indent=2)
    logger.info("Final report saved to %s", final_report_path)


if __name__ == "__main__":
    main()
