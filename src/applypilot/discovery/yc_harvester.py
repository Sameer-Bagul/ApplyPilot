"""Y Combinator Harvester & VIP Lead Enricher.

Fetches launched and actively hiring Y Combinator startups globally, in India,
and remote directly from the public YC OSS API (yc-oss.github.io/api) with zero rate limits.

Features:
- Zero-token static JSON ingestion (1,504 hiring startups, 6,362 launched startups).
- Filter by India (Bengaluru, Mumbai, Delhi NCR, Pune, Hyderabad, etc.) and Remote.
- Automated founder name extraction from company profiles.
- Upserts to career_watchlist with priority_tier=1, is_vip=1, source='yc_oss'.
- Runs deep email synthesis (5-10 verified emails per startup) via Google DoH.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from applypilot.database import (
    get_connection,
    store_recruiter_lead,
    upsert_career_watchlist,
)
from applypilot.discovery.bangalore_map_harvester import (
    check_domain_mx,
    enrich_startup_emails_deep,
)

logger = logging.getLogger(__name__)

YC_HIRING_API = "https://yc-oss.github.io/api/companies/hiring.json"
YC_ALL_API = "https://yc-oss.github.io/api/companies/all.json"
YC_TOP_API = "https://yc-oss.github.io/api/companies/top.json"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

INDIAN_CITY_KEYWORDS = {
    "india",
    "bengaluru",
    "bangalore",
    "mumbai",
    "delhi",
    "new delhi",
    "gurgaon",
    "gurugram",
    "noida",
    "pune",
    "hyderabad",
    "chennai",
    "kolkata",
    "ahmedabad",
    "kochi",
    "indore",
}

FOUNDER_REGEX = re.compile(
    r"([A-Z][a-z]+ [A-Z][a-z]+)\s*\((?:CEO|CTO|MD|CPO|COO|Co-Founder|Founder)[^)]*\)",
)


def extract_founders_from_text(text: str | None) -> list[str]:
    """Extract founder names from YC company descriptions using heuristic pattern matching."""
    if not text:
        return []
    matches = FOUNDER_REGEX.findall(text)
    founders: list[str] = []
    seen: set[str] = set()
    for m in matches:
        clean = m.strip()
        if clean.lower() not in seen and len(clean.split()) == 2:
            seen.add(clean.lower())
            founders.append(clean)
    return founders


def fetch_yc_startups_raw(
    hiring_only: bool = True,
    timeout: float = 20.0,
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """Fetch raw startup list from public YC OSS API."""
    url = YC_HIRING_API if hiring_only else YC_ALL_API
    should_close = False
    if client is None:
        client = httpx.Client(headers=DEFAULT_HEADERS, timeout=timeout)
        should_close = True

    try:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("Failed to fetch YC startups from %s: %s", url, exc)
        return []
    finally:
        if should_close:
            client.close()


def is_indian_yc_startup(company: dict[str, Any]) -> bool:
    """Check if a YC startup has an active location or headquarters in India."""
    all_locations = (company.get("all_locations") or "").lower()
    regions = [r.lower() for r in (company.get("regions") or [])]
    tags = [t.lower() for t in (company.get("tags") or [])]

    if "india" in regions or "india" in tags:
        return True

    for city in INDIAN_CITY_KEYWORDS:
        if city in all_locations:
            return True
    return False


def is_remote_yc_startup(company: dict[str, Any]) -> bool:
    """Check if a YC startup supports remote or partly remote hiring."""
    regions = [r.lower() for r in (company.get("regions") or [])]
    all_locations = (company.get("all_locations") or "").lower()
    return "remote" in regions or "partly remote" in regions or "remote" in all_locations


def normalize_yc_startup(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a raw YC startup entry into standard ApplyPilot schema."""
    name = (raw.get("name") or "").strip()
    website = (raw.get("website") or "").strip()
    domain = None
    if website:
        parsed = urlparse(website if website.startswith("http") else f"https://{website}")
        domain = parsed.netloc.lower().replace("www.", "")

    description = raw.get("long_description") or raw.get("one_liner") or ""
    founders = extract_founders_from_text(description)

    return {
        "id": raw.get("id"),
        "name": name,
        "slug": raw.get("slug"),
        "domain": domain,
        "website": website,
        "location": raw.get("all_locations") or "Remote / Global",
        "batch": raw.get("batch"),
        "stage": raw.get("stage") or "Early",
        "team_size": raw.get("team_size") or 0,
        "is_hiring": raw.get("isHiring", True),
        "one_liner": raw.get("one_liner") or "",
        "tags": raw.get("tags") or [],
        "founders": founders,
        "yc_url": raw.get("url") or f"https://www.ycombinator.com/companies/{raw.get('slug', '')}",
        "source": "yc_oss",
    }


def fetch_yc_startups(
    india_only: bool = False,
    remote_only: bool = False,
    hiring_only: bool = True,
    limit: int | None = None,
    timeout: float = 20.0,
) -> list[dict[str, Any]]:
    """Fetch and filter normalized YC startups.

    Args:
        india_only: If True, keep only companies in Bangalore/India.
        remote_only: If True, keep companies offering Remote roles.
        hiring_only: If True, fetch companies currently hiring (default True).
        limit: Max number of startups to return.
        timeout: HTTP request timeout in seconds.
    """
    raw_list = fetch_yc_startups_raw(hiring_only=hiring_only, timeout=timeout)
    normalized: list[dict[str, Any]] = []

    for raw in raw_list:
        if india_only and not is_indian_yc_startup(raw):
            continue
        if remote_only and not is_remote_yc_startup(raw):
            continue

        item = normalize_yc_startup(raw)
        if item["name"]:
            normalized.append(item)
            if limit and len(normalized) >= limit:
                break

    logger.info(
        "Fetched %d YC startups (india_only=%s, remote_only=%s, hiring_only=%s)",
        len(normalized),
        india_only,
        remote_only,
        hiring_only,
    )
    return normalized


def ingest_yc_startups_to_db(
    startups: list[dict[str, Any]],
    enrich_emails: bool = True,
    target_emails_per_startup: int = 6,
    conn: Any = None,
) -> dict[str, int]:
    """Ingest YC startups into career_watchlist and optionally run deep email looper."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    stats = {
        "startups_ingested": 0,
        "emails_enriched": 0,
        "leads_created": 0,
        "domains_verified": 0,
    }

    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        for s in startups:
            name = s["name"]
            domain = s.get("domain")
            website = s.get("website")
            batch = s.get("batch") or "Unknown"
            stage = s.get("stage") or "Early"
            one_liner = s.get("one_liner") or ""
            founders = s.get("founders") or []
            founders_str = ", ".join(founders) if founders else None

            notes = f"YC {batch} | {stage} | {one_liner}".strip(" |")

            # 1. Upsert to career_watchlist as VIP Tier 1
            upsert_career_watchlist(
                company_name=name,
                official_domain=domain,
                careers_page_url=website,
                ats_provider=None,
                ats_board_token=None,
                priority_tier=1,
                is_vip=1,
                stage=stage,
                founders_json=json.dumps(founders) if founders else None,
                conn=conn,
            )
            stats["startups_ingested"] += 1

            # 2. Deep Email Enrichment Loop
            if enrich_emails and domain:
                mx_ok = check_domain_mx(domain)
                if mx_ok:
                    stats["domains_verified"] += 1
                    leads = enrich_startup_emails_deep(
                        company_name=name,
                        domain=domain,
                        website_url=website,
                        founders=founders,
                        target_count=target_emails_per_startup,
                    )
                    stats["emails_enriched"] += len(leads)
                    for l in leads:
                        try:
                            c_type = "founder" if "founder" in l.get("type", "") else "recruiter"
                            store_recruiter_lead(
                                contact_email=l["email"],
                                role_title=f"{'Founder / Executive' if c_type == 'founder' else 'Talent / HR'} at {name}",
                                company_name=name,
                                company_domain=domain,
                                contact_name=l.get("contact_name") or f"{name} Hiring",
                                contact_type=c_type,
                                source_platform="yc_oss",
                                source_post_url=s.get("yc_url"),
                                evidence_snippet=one_liner or f"YC {batch} startup in {s.get('location')}",
                                execution_route="DUAL_ATTACK" if website else "EMAIL_ONLY",
                                conn=conn,
                            )
                            stats["leads_created"] += 1
                        except Exception:
                            pass
        conn.commit()
    finally:
        if should_close:
            conn.close()

    logger.info("YC Startups ingestion complete: %s", stats)
    return stats
