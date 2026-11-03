"""StartupMap.one Directory & Job Harvester.

Scrapes curated startups and live startup jobs from startupmap.one:
- Bangalore Startup Jobs feed: https://startupmap.one/jobs/bangalore
- Remote Startup Jobs feed: https://startupmap.one/jobs/remote

Extracts:
1. Startup name and website domain
2. Open job titles, locations, and direct ATS outbound application links
3. Upserts to career_watchlist and stores jobs into jobs table.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import urlparse

import httpx

from applypilot.career_resolver.jsonld_parser import extract_jsonld_jobpostings
from applypilot.database import (
    get_connection,
    store_jobs,
    store_recruiter_lead,
    upsert_career_watchlist,
)
from applypilot.discovery.bangalore_map_harvester import (
    enrich_startup_emails_deep,
)

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

STARTUPMAP_BLR_URL = "https://startupmap.one/jobs/bangalore"
STARTUPMAP_REMOTE_URL = "https://startupmap.one/jobs/remote"


def fetch_startupmap_html(url: str = STARTUPMAP_BLR_URL, timeout: float = 20.0) -> str:
    """Fetch raw HTML from startupmap.one."""
    with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=timeout) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text


def parse_startupmap_jobs(html: str) -> list[dict[str, Any]]:
    """Parse startup jobs from startupmap.one HTML or embedded JSON-LD."""
    jobs: list[dict[str, Any]] = []

    # 1. Embedded JSON-LD schema
    jsonld_jobs = extract_jsonld_jobpostings(html)
    for j in jsonld_jobs:
        jobs.append({
            "title": j["title"],
            "company_name": j.get("company", ""),
            "company_domain": None,
            "ats_url": j.get("url"),
            "location": j.get("location", "Bengaluru, India"),
            "description": j.get("description", ""),
        })

    # 2. HTML Card extraction fallback
    # Pattern: job card with title, company, and outbound link
    card_pattern = re.compile(
        r'<a[^>]*href="([^"]+)"[^>]*>\s*<h[2-4][^>]*>([^<]+)</h[2-4]>.*?'
        r'(?:at|by|company)\s+<span[^>]*>([^<]+)</span>',
        re.DOTALL | re.IGNORECASE,
    )

    for m in card_pattern.finditer(html):
        url, title, company = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        if any(ats in url for ats in ["greenhouse.io", "lever.co", "ashbyhq.com", "workday", "workable.com"]):
            jobs.append({
                "title": title,
                "company_name": company,
                "company_domain": None,
                "ats_url": url,
                "location": "Bengaluru, India",
                "description": "",
            })

    return jobs


def ingest_startupmap_jobs_to_db(
    jobs: list[dict[str, Any]],
    enrich_emails: bool = True,
    target_emails_per_startup: int = 6,
    conn: Any = None,
) -> dict[str, Any]:
    """Ingest startupmap.one jobs and companies into database."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    stats = {
        "companies_ingested": 0,
        "jobs_stored": 0,
        "leads_created": 0,
    }

    companies: dict[str, list[dict[str, Any]]] = {}
    for j in jobs:
        c_name = j.get("company_name", "").strip()
        if not c_name:
            continue
        companies.setdefault(c_name, []).append(j)

    with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=8.0) as client:
        for c_name, j_list in companies.items():
            first_job = j_list[0]
            ats_url = first_job.get("ats_url")
            domain = None
            if ats_url:
                try:
                    parsed = urlparse(ats_url)
                    if not any(ats in parsed.netloc for ats in ["greenhouse.io", "lever.co", "ashbyhq.com", "workday"]):
                        domain = parsed.netloc.lower().replace("www.", "")
                except Exception:
                    pass

            upsert_career_watchlist(
                company_name=c_name,
                official_domain=domain,
                careers_page_url=ats_url,
                priority_tier=2,
                is_vip=0,
                sector="Startups",
                open_roles_count=len(j_list),
                conn=conn,
            )
            stats["companies_ingested"] += 1

            # Store jobs
            for j in j_list:
                job_url = j.get("ats_url")
                if not job_url:
                    continue
                try:
                    new_cnt, _ = store_jobs(
                        conn=conn,
                        jobs=[{
                            "url": job_url,
                            "title": j.get("title", f"Role at {c_name}"),
                            "location": j.get("location", "Bengaluru, India"),
                        }],
                        site="startupmap.one",
                        strategy="startupmap_one_harvester",
                    )
                    conn.execute("UPDATE jobs SET company = ? WHERE url = ?", (c_name, job_url))
                    conn.commit()
                    if new_cnt > 0:
                        stats["jobs_stored"] += 1
                except Exception:
                    pass

    if should_close:
        conn.close()

    return stats
