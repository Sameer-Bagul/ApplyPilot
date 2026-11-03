"""Tech Company Search Engine Pipeline & Autonomous Downstream Handoff.

A high-signal search engine pipeline that:
1. Dynamically discovers tech companies and funded startups across search engines
   (DuckDuckGo dorks), YC directories, and VC ecosystems.
2. Ingests company profile: name, official domain, careers URL, sector, stage,
   headquarters/location, team size, and funding status.
3. Automatically enrolls companies into `career_watchlist`.
4. Hands off discovered companies to downstream workers:
   - Worker 1 (Career Page & ATS Investigator): scans careers page, detects ATS provider,
     and scrapes live job openings.
   - Worker 2 (Deep Executive & Recruiter Looper): searches CEO, CTO, VP Engineering,
     and recruiters, runs Google DoH MX verification, and creates `recruiter_leads`.
   - Worker 3 (Dual-Attack Classifier): synchronizes execution routes (DUAL_ATTACK,
     EMAIL_ONLY, PORTAL_ONLY).
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

from applypilot.database import (
    get_connection,
    store_jobs,
    store_recruiter_lead,
    sync_discovered_companies_from_jobs_and_leads,
    sync_execution_routes,
    upsert_career_watchlist,
)
from applypilot.discovery.bangalore_map_harvester import (
    check_domain_mx,
    enrich_startup_emails_deep,
)
from applypilot.discovery.company_deep_looper import loop_and_enrich_single_company

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/json,*/*",
}

TECH_SECTOR_KEYWORDS = {
    "AI / Machine Learning": ["ai", "artificial intelligence", "llm", "machine learning", "deep learning", "agentic", "neural", "vision"],
    "Enterprise SaaS": ["saas", "crm", "workflow", "sales", "enterprise", "productivity", "hrtech", "b2b"],
    "Fintech & Crypto": ["fintech", "payments", "banking", "crypto", "defi", "web3", "lending", "credit", "wealth"],
    "Developer Tools & Cloud": ["devtool", "developer", "cloud", "infra", "kubernetes", "database", "observability", "devtools"],
    "Cybersecurity": ["security", "cyber", "zero-trust", "threat", "auth", "compliance"],
    "Robotics & Hard Tech": ["robotics", "hardware", "iot", "sensor", "space", "semiconductor", "autonomous"],
}

DEFAULT_SEARCH_QUERIES = [
    '"fastest growing tech startups" "seed" OR "series a" "careers"',
    '"top AI startups" "hiring software engineers" "careers" OR "jobs"',
    '"funded tech companies" "software engineer" "Bengaluru" OR "remote" "careers"',
    '"series a" OR "series b" developer tools infra startups hiring',
    '"YC W24" OR "YC S24" OR "YC W25" hiring software engineer careers',
    'site:greenhouse.io OR site:lever.co OR site:ashbyhq.com "staff software engineer" startup',
]


def classify_tech_sector(text: str) -> str:
    """Classify sector based on text clues."""
    lower = text.lower()
    for sector, keywords in TECH_SECTOR_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return sector
    return "Technology / Software"


def extract_clean_domain(url: str) -> str | None:
    """Extract official clean domain from URL, ignoring aggregators."""
    if not url or not url.startswith("http"):
        return None
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower().replace("www.", "")
        # Filter out generic search engines or job boards
        ignored = [
            "duckduckgo.com", "google.com", "bing.com", "linkedin.com", "github.com",
            "twitter.com", "x.com", "youtube.com", "medium.com", "substack.com",
            "wikipedia.org", "ycombinator.com", "topstartups.io", "techcrunch.com",
            "wellfound.com", "angel.co", "glassdoor.com", "indeed.com",
        ]
        if any(ign in host for ign in ignored):
            return None
        return host
    except Exception:
        return None


def search_tech_companies_via_dorks(
    query_list: list[str] | None = None,
    max_results_per_query: int = 15,
    conn: Any = None,
) -> list[dict[str, Any]]:
    """Query search engines (DuckDuckGo & backends) to discover emerging tech companies."""
    queries = query_list or DEFAULT_SEARCH_QUERIES
    discovered_companies: list[dict[str, Any]] = []
    seen_domains: set[str] = set()

    try:
        from ddgs import DDGS
        with DDGS(timeout=10) as ddgs:
            for q in queries:
                hits = []
                for backend in ["duckduckgo", "auto", "startpage", "brave"]:
                    try:
                        hits = list(ddgs.text(q, backend=backend, max_results=max_results_per_query))
                        if hits:
                            break
                    except Exception:
                        continue

                for h in hits:
                    href = h.get("href", "")
                    title = h.get("title", "")
                    snippet = h.get("body", "")

                    domain = extract_clean_domain(href)
                    if not domain or domain in seen_domains:
                        continue

                    seen_domains.add(domain)

                    # Extract company name from title or domain
                    # e.g. "Careers | Cursor" -> "Cursor"
                    clean_name = title.split("|")[0].split(" - ")[0].split(" – ")[0].strip()
                    clean_name = re.sub(r"(?i)\b(careers|jobs|hiring|openings|home|official site)\b", "", clean_name).strip()
                    if not clean_name or len(clean_name) > 40:
                        clean_name = domain.split(".")[0].capitalize()

                    # Detect ATS provider in URL
                    ats_provider = None
                    careers_url = href
                    for ats in ["greenhouse.io", "lever.co", "ashbyhq.com", "myworkdayjobs.com", "workable.com"]:
                        if ats in href:
                            ats_provider = ats.split(".")[0]
                            break

                    sector = classify_tech_sector(title + " " + snippet)

                    discovered_companies.append({
                        "company_name": clean_name,
                        "official_domain": domain,
                        "careers_page_url": careers_url,
                        "ats_provider": ats_provider,
                        "sector": sector,
                        "stage": "Funded Tech Startup",
                        "location": "Global / Remote",
                        "source": "search_engine_dork",
                        "snippet": snippet,
                    })

                time.sleep(0.3)
    except Exception as e:
        logger.warning("Search engine tech company discovery error: %s", e)

    return discovered_companies


def fetch_yc_tech_startups(
    limit: int = 50,
    only_hiring: bool = True,
) -> list[dict[str, Any]]:
    """Fetch high-signal launched and actively hiring tech companies from YC OSS API."""
    url = "https://yc-oss.github.io/api/companies/hiring.json" if only_hiring else "https://yc-oss.github.io/api/companies/top.json"
    companies: list[dict[str, Any]] = []

    try:
        with httpx.Client(headers=DEFAULT_HEADERS, timeout=10.0, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                for item in data[:limit]:
                    name = item.get("name")
                    if not name:
                        continue

                    website = item.get("website", "")
                    domain = extract_clean_domain(website) or (name.lower().replace(" ", "") + ".com")
                    industry = item.get("industry") or item.get("subindustry") or "Technology"
                    team_size = str(item.get("team_size") or "10-50")
                    stage = item.get("stage") or ("Top YC" if item.get("top_company") else "Early Stage")
                    locations = item.get("all_locations") or "San Francisco / Remote"
                    desc = item.get("one_liner") or item.get("long_description", "")

                    founders = []
                    # Infer founders if mentioned in description
                    desc_lower = desc.lower()

                    companies.append({
                        "company_name": name,
                        "official_domain": domain,
                        "careers_page_url": f"https://www.ycombinator.com/companies/{item.get('slug', '')}",
                        "ats_provider": "yc_job_board",
                        "sector": classify_tech_sector(industry + " " + desc),
                        "stage": stage,
                        "location": locations,
                        "team_size": team_size,
                        "source": "yc_oss_api",
                        "snippet": desc[:250],
                    })
    except Exception as e:
        logger.warning("YC tech company ingestion error: %s", e)

    return companies


def run_tech_company_search_engine(
    queries: list[str] | None = None,
    include_yc: bool = True,
    yc_limit: int = 40,
    dork_results_limit: int = 15,
    auto_handoff_workers: bool = True,
    max_workers_handoff: int = 10,
    conn: Any = None,
) -> dict[str, Any]:
    """Execute complete Tech Company Search Engine Pipeline with autonomous downstream handoff.

    1. Searches web & directories for tech companies.
    2. Enrolls and updates `career_watchlist`.
    3. Triggers downstream workers (ATS investigator + executive recruiter looper + route sync).
    """
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    t0 = time.time()
    discovered_list: list[dict[str, Any]] = []

    # 1. Search Engine Dorks
    dork_companies = search_tech_companies_via_dorks(
        query_list=queries,
        max_results_per_query=dork_results_limit,
        conn=conn,
    )
    discovered_list.extend(dork_companies)

    # 2. YC High-Signal Ingestion
    if include_yc:
        yc_companies = fetch_yc_tech_startups(limit=yc_limit, only_hiring=True)
        discovered_list.extend(yc_companies)

    # 3. Synchronize existing companies from jobs & recruiter_leads
    sync_res = sync_discovered_companies_from_jobs_and_leads(conn=conn)

    # 4. Enroll all newly discovered companies into career_watchlist
    enrolled_count = 0
    enrolled_cids = []
    for comp in discovered_list:
        try:
            cid = upsert_career_watchlist(
                company_name=comp["company_name"],
                official_domain=comp.get("official_domain"),
                careers_page_url=comp.get("careers_page_url"),
                ats_provider=comp.get("ats_provider"),
                sector=comp.get("sector", "Technology"),
                stage=comp.get("stage", "Funded Tech Startup"),
                location=comp.get("location", "Remote"),
                team_size=comp.get("team_size"),
                priority_tier=1 if comp.get("source") == "yc_oss_api" else 2,
                is_vip=1 if comp.get("source") == "yc_oss_api" else 0,
                conn=conn,
            )
            if cid:
                enrolled_count += 1
                enrolled_cids.append(cid)
        except Exception as e:
            logger.debug("Enrollment notice for %s: %s", comp.get("company_name"), e)

    # 5. Autonomous Downstream Worker Handoff
    # Other workers hop in: Career Page Investigator & Deep Executive Recruiter Looper
    handoff_results = []
    if auto_handoff_workers and discovered_list:
        sample_candidates = discovered_list[:max_workers_handoff]
        with httpx.Client(headers=DEFAULT_HEADERS, timeout=8.0, follow_redirects=True) as client:
            for c_cand in sample_candidates:
                try:
                    res_loop = loop_and_enrich_single_company(
                        company=c_cand,
                        enrich_emails=True,
                        poll_jobs=True,
                        target_emails=6,
                        client=client,
                        conn=conn,
                    )
                    handoff_results.append(res_loop)
                except Exception as loop_err:
                    logger.debug("Downstream worker handoff notice for %s: %s", c_cand.get("company_name"), loop_err)

    # 6. Synchronize Execution Routes
    route_stats = sync_execution_routes(conn=conn)

    duration = round(time.time() - t0, 2)
    total_in_db = conn.execute("SELECT COUNT(*) FROM career_watchlist").fetchone()[0]

    result = {
        "status": "success",
        "duration_seconds": duration,
        "companies_discovered": len(discovered_list),
        "companies_enrolled": enrolled_count,
        "total_companies_in_watchlist": total_in_db,
        "downstream_workers_executed": len(handoff_results),
        "handoff_summary": handoff_results[:5],
        "route_stats": route_stats,
    }

    if should_close:
        conn.close()

    return result


def deep_research_single_company(
    company_name: str,
    conn: Any = None,
) -> dict[str, Any]:
    """Execute on-demand deep research worker for a specific company:
    searches latest jobs, official careers portal, and executive/recruiter inboxes.
    """
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    row = conn.execute(
        "SELECT * FROM career_watchlist WHERE LOWER(company_name) = LOWER(?)",
        (company_name.strip(),),
    ).fetchone()

    company_dict: dict[str, Any] = {}
    if row:
        company_dict = dict(row)
    else:
        # Enroll minimal
        company_dict = {
            "company_name": company_name.strip(),
            "official_domain": None,
            "careers_page_url": None,
        }

    with httpx.Client(headers=DEFAULT_HEADERS, timeout=10.0, follow_redirects=True) as client:
        res = loop_and_enrich_single_company(
            company=company_dict,
            enrich_emails=True,
            poll_jobs=True,
            target_emails=8,
            client=client,
            conn=conn,
        )

    # Sync routes
    sync_execution_routes(conn=conn)

    # Refresh counts
    updated_jobs = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE company = ?", (company_name.strip(),)
    ).fetchone()[0]
    updated_leads = conn.execute(
        "SELECT COUNT(*) FROM recruiter_leads WHERE company_name = ?", (company_name.strip(),)
    ).fetchone()[0]

    conn.execute(
        "UPDATE career_watchlist SET open_roles_count = ? WHERE LOWER(company_name) = LOWER(?)",
        (updated_jobs, company_name.strip()),
    )
    conn.commit()

    res["total_jobs"] = updated_jobs
    res["total_emails"] = updated_leads

    if should_close:
        conn.close()

    return res
