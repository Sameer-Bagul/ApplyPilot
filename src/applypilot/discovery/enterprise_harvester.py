"""Enterprise Fortune 500 & Global Capability Center (GCC) Harvester.

Targets premier banking, fintech, Big Tech, and global enterprise GCCs
that host their career portals on Workday, iCIMS, Taleo, and custom ATSs.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from rich.console import Console

from applypilot.database import get_connection, upsert_career_watchlist
from applypilot.discovery.freehire_harvester import FreeHireClient, ingest_freehire_jobs

logger = logging.getLogger("applypilot.enterprise")
console = Console()

# Premier Enterprise & Global Capability Center (GCC) Roster with verified FreeHire company slugs
ENTERPRISE_ROSTER: list[dict[str, Any]] = [
    # Top Tier Investment Banks & FinTech Giants
    {"name": "Barclays", "slug": "barclays", "sector": "Investment Banking", "ats": "workday"},
    {"name": "Mastercard", "slug": "mastercard", "sector": "Payments / FinTech", "ats": "workday"},
    {"name": "Visa", "slug": "visa", "sector": "Payments / FinTech", "ats": "smartrecruiters"},
    {"name": "American Express", "slug": "american-express", "sector": "FinTech / Banking", "ats": "workday"},
    {"name": "JPMorgan Chase", "slug": "jpmc", "sector": "Investment Banking", "ats": "workday"},
    {"name": "Goldman Sachs", "slug": "goldman-sachs", "sector": "Investment Banking", "ats": "workday"},
    {"name": "Morgan Stanley", "slug": "morgan-stanley", "sector": "Investment Banking", "ats": "workday"},
    {"name": "Citi", "slug": "citi", "sector": "Banking / GCC", "ats": "workday"},
    {"name": "Wells Fargo", "slug": "wells-fargo", "sector": "Banking / GCC", "ats": "workday"},
    {"name": "HSBC", "slug": "hsbc", "sector": "Banking / GCC", "ats": "taleo"},
    {"name": "Deutsche Bank", "slug": "deutsche-bank", "sector": "Banking / GCC", "ats": "workday"},
    {"name": "BlackRock", "slug": "blackrock", "sector": "Asset Management", "ats": "workday"},
    {"name": "Standard Chartered", "slug": "standard-chartered", "sector": "Banking / GCC", "ats": "taleo"},
    {"name": "BNY Mellon", "slug": "bny-mellon", "sector": "Asset Management", "ats": "workday"},
    {"name": "Fidelity Investments", "slug": "fidelity", "sector": "Asset Management", "ats": "workday"},

    # Big Tech & Enterprise Platforms
    {"name": "Microsoft", "slug": "microsoft", "sector": "Enterprise Tech", "ats": "custom"},
    {"name": "Amazon", "slug": "amazon", "sector": "Cloud & E-Commerce", "ats": "custom"},
    {"name": "Google", "slug": "google", "sector": "Big Tech / AI", "ats": "custom"},
    {"name": "Nvidia", "slug": "nvidia", "sector": "AI & Semis", "ats": "workday"},
    {"name": "Oracle", "slug": "oracle", "sector": "Enterprise Cloud", "ats": "oracle"},
    {"name": "Cisco", "slug": "cisco", "sector": "Networking / Cloud", "ats": "workday"},
    {"name": "Salesforce", "slug": "salesforce", "sector": "CRM / Cloud", "ats": "workday"},
    {"name": "Adobe", "slug": "adobe", "sector": "SaaS / Design AI", "ats": "workday"},
    {"name": "Walmart Global Tech", "slug": "walmart", "sector": "Retail Tech GCC", "ats": "workday"},
]


def seed_enterprise_watchlist(conn: sqlite3.Connection | None = None) -> int:
    """Seed enterprise roster into career_watchlist with priority_tier=1."""
    if conn is None:
        conn = get_connection()
    added = 0
    for comp in ENTERPRISE_ROSTER:
        try:
            upsert_career_watchlist(
                company_name=comp["name"],
                official_domain=f"{comp['slug']}.com",
                careers_page_url=f"https://{comp['slug']}.com/careers",
                ats_provider=comp.get("ats", "workday"),
                priority_tier=1,  # VIP Enterprise
                is_vip=1,
                sector=comp.get("sector"),
                conn=conn,
            )
            added += 1
        except Exception as e:
            logger.debug("Notice seeding %s: %s", comp["name"], e)
    return added


def harvest_enterprise_companies(
    companies: list[str] | None = None,
    limit_per_company: int = 25,
    countries: list[str] | None = None,
    conn: sqlite3.Connection | None = None,
    client: FreeHireClient | None = None,
) -> dict[str, Any]:
    """Harvest open roles from premier enterprise giants and GCCs."""
    if client is None:
        client = FreeHireClient()
    if conn is None:
        conn = get_connection()

    # Ensure companies are seeded into watchlist
    seed_enterprise_watchlist(conn=conn)

    target_roster = ENTERPRISE_ROSTER
    if companies:
        normalized = [c.lower().strip() for c in companies]
        target_roster = [
            c for c in ENTERPRISE_ROSTER
            if c["slug"] in normalized or any(n in c["name"].lower() for n in normalized)
        ]

    summary = {
        "companies_scanned": len(target_roster),
        "total_jobs_fetched": 0,
        "new_jobs_stored": 0,
        "existing_jobs": 0,
        "company_details": {},
    }

    for comp in target_roster:
        slug = comp["slug"]
        name = comp["name"]
        logger.info("Harvesting enterprise giant: %s (%s)...", name, slug)

        try:
            # Query without restricting work_mode (catches onsite campus roles as well as hybrid/remote)
            res = client.search_jobs(
                company_slugs=[slug],
                countries=countries,  # None = Global or ['in'] = India
                limit=limit_per_company,
            )
            jobs = res.get("jobs", [])
            total_in_cat = res.get("total", len(jobs))

            if jobs:
                stats = ingest_freehire_jobs(jobs, conn=conn, client=client)
                summary["total_jobs_fetched"] += len(jobs)
                summary["new_jobs_stored"] += stats.get("new", 0)
                summary["existing_jobs"] += stats.get("existing", 0)
                summary["company_details"][name] = {
                    "total_available": total_in_cat,
                    "scraped": len(jobs),
                    "new_stored": stats.get("new", 0),
                }
            else:
                summary["company_details"][name] = {"total_available": total_in_cat, "scraped": 0, "new_stored": 0}

        except Exception as e:
            logger.warning("Failed harvesting %s: %s", name, e)
            summary["company_details"][name] = {"error": str(e)}

    return summary
