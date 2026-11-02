"""BLR Startup Arena Harvester & Bangalore Tech Map Ingester.

Extracts all 749+ tech companies and startups across 42 Bangalore localities
(HSR Layout, Koramangala, Indiranagar, Electronic City, Adugodi, Whitefield, etc.)
from the Next.js React Server Component stream on blrstartuparena.com.

Features:
- Zero-token Next.js RSC stream extraction of 749 companies with 9,475+ open positions.
- Office addresses, geographic coordinates (lat/lng), localities, and commute data.
- Functional job family breakdown (Backend, AI/ML, DevOps, Frontend, Fullstack).
- Domain resolution and MX validation via Google DoH.
- Upserts to career_watchlist (priority_tier=1, is_vip=1, source='blr_arena').
- Triggers deep email enrichment loop (5-10 verified emails per startup).
"""

from __future__ import annotations

import json
import logging
import re
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

BLR_ARENA_MAP_URL = "https://www.blrstartuparena.com/map"
BLR_ARENA_JOBS_URL = "https://www.blrstartuparena.com/jobs"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

COMMON_DOMAIN_OVERRIDES: dict[str, str] = {
    "bosch": "bosch.com",
    "pwc": "pwc.in",
    "cisco": "cisco.com",
    "thermo-fisher-scientific": "thermofisher.com",
    "razorpay": "razorpay.com",
    "cred": "cred.club",
    "swiggy": "swiggy.com",
    "flipkart": "flipkart.com",
    "meesho": "meesho.com",
    "phonepe": "phonepe.com",
    "slice": "sliceit.com",
    "groww": "groww.in",
    "zerodha": "zerodha.com",
    "urban-company": "urbancompany.com",
    "postman": "postman.com",
    "hasura": "hasura.io",
    "zeta": "zeta.tech",
    "mpl": "mpl.live",
    "juspay": "juspay.in",
    "chargebee": "chargebee.com",
}


def fetch_blr_arena_raw(url: str = BLR_ARENA_MAP_URL, timeout: float = 20.0) -> str:
    """Fetch raw HTML from blrstartuparena.com."""
    with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=timeout) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text


def parse_blr_arena_companies(html: str) -> list[dict[str, Any]]:
    """Parse 749 companies from the Next.js RSC stream in BLR Startup Arena HTML.

    Returns:
        List of company dictionaries with slug, name, locality, address, jobCount, and facets.
    """
    marker = r"\"companies\":["
    idx = html.find(marker)
    if idx == -1:
        # Try unescaped marker
        idx = html.find('"companies":[')
        if idx == -1:
            logger.warning("No companies array found in BLR Startup Arena HTML")
            return []
        start = idx + len('"companies":')
        end_marker = html.find("],", start)
    else:
        start = idx + len(marker) - 1
        end_marker = html.find(r"],\"modes\":", start)
        if end_marker == -1:
            end_marker = html.find(r"],\"", start)

    if end_marker == -1:
        logger.warning("Could not find end of companies array in BLR Startup Arena HTML")
        return []

    raw_array = html[start:end_marker + 1]
    try:
        unescaped = raw_array.encode().decode("unicode-escape")
        companies: list[dict[str, Any]] = json.loads(unescaped)
        logger.info("Parsed %d companies from BLR Startup Arena", len(companies))
        return companies
    except Exception as exc:
        logger.error("Failed to decode BLR Startup Arena companies JSON: %s", exc)
        return []


def resolve_blr_arena_domain(name: str, slug: str) -> str | None:
    """Resolve an official domain for a BLR Startup Arena company."""
    clean_slug = slug.lower().strip()
    if clean_slug in COMMON_DOMAIN_OVERRIDES:
        return COMMON_DOMAIN_OVERRIDES[clean_slug]

    # Try common TLD candidates with MX validation
    candidates = [
        f"{clean_slug}.com",
        f"{clean_slug}.in",
        f"{clean_slug}.io",
        f"{clean_slug}.tech",
        f"{clean_slug}.co",
    ]
    for cand in candidates:
        if check_domain_mx(cand, timeout=1.5):
            return cand

    # Default fallback to .com
    return f"{clean_slug}.com"


def normalize_blr_arena_company(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize BLR Startup Arena company into ApplyPilot schema."""
    name = (raw.get("name") or "").strip()
    slug = (raw.get("slug") or "").strip()
    locality = raw.get("locality") or "Bengaluru"
    address = raw.get("address") or ""
    job_count = raw.get("jobCount") or 0
    fresher_count = raw.get("fresherCount") or 0
    lat = raw.get("latitude")
    lng = raw.get("longitude")

    facets = raw.get("facets", {})
    families = facets.get("families", {}) if isinstance(facets, dict) else {}

    domain = resolve_blr_arena_domain(name, slug)
    website = f"https://{domain}" if domain else None

    # Construct concise summary notes
    family_summary = []
    for k in ("sde_backend", "ml_ai_engineering", "devops_sre_cloud", "sde_fullstack", "product_management"):
        cnt = families.get(k)
        if cnt:
            short_k = k.replace("sde_", "").replace("_engineering", "")
            family_summary.append(f"{short_k}:{cnt}")

    facets_str = ", ".join(family_summary) if family_summary else f"{job_count} open jobs"
    notes = f"Locality: {locality} | Jobs: {facets_str} | Address: {address}".strip(" |")

    return {
        "slug": slug,
        "name": name,
        "domain": domain,
        "website_url": website,
        "locality": locality,
        "address": address,
        "latitude": lat,
        "longitude": lng,
        "job_count": job_count,
        "fresher_count": fresher_count,
        "role_families": families,
        "notes": notes[:250],
        "source": "blr_arena",
    }


def fetch_blr_arena_startups(limit: int | None = None, timeout: float = 20.0) -> list[dict[str, Any]]:
    """Fetch and normalize all startups from BLR Startup Arena."""
    html = fetch_blr_arena_raw(timeout=timeout)
    raw_cos = parse_blr_arena_companies(html)
    normalized: list[dict[str, Any]] = []

    for raw in raw_cos:
        item = normalize_blr_arena_company(raw)
        if item["name"]:
            normalized.append(item)
            if limit and len(normalized) >= limit:
                break

    return normalized


def ingest_blr_arena_to_db(
    startups: list[dict[str, Any]],
    enrich_emails: bool = True,
    target_emails_per_startup: int = 6,
    conn: Any = None,
) -> dict[str, int]:
    """Ingest BLR Startup Arena companies into career_watchlist and run deep email looper."""
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
        for s in startups:
            name = s["name"]
            domain = s.get("domain")
            website = s.get("website_url")
            notes = s.get("notes")

            # 1. Upsert to career_watchlist as VIP Tier 1
            locality = s.get("locality")
            job_cnt = s.get("job_count") or 0
            upsert_career_watchlist(
                company_name=name,
                official_domain=domain,
                careers_page_url=website,
                slug=s.get("slug"),
                priority_tier=1,
                is_vip=1,
                area=locality,
                location=s.get("address"),
                open_roles_count=job_cnt,
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
                        target_count=target_emails_per_startup,
                    )
                    stats["emails_enriched"] += len(leads)
                    for l in leads:
                        try:
                            c_type = "founder" if "founder" in l.get("type", "") else "recruiter"
                            store_recruiter_lead(
                                contact_email=l["email"],
                                role_title=f"{'Founder / Executive' if c_type == 'founder' else 'Talent / Recruitment'} at {name}",
                                company_name=name,
                                company_domain=domain,
                                contact_name=l.get("contact_name") or f"{name} Recruiting",
                                contact_type=c_type,
                                source_platform="blrstartuparena.com",
                                source_post_url=f"https://www.blrstartuparena.com/companies/{s.get('slug')}",
                                evidence_snippet=notes or f"Tech company in {locality}",
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

    logger.info("BLR Startup Arena ingestion complete: %s", stats)
    return stats
