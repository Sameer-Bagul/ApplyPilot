"""TopStartups.io Harvester & VIP ATS Job Ingester.

Scrapes newly funded, high-signal tech startups and direct ATS job applications
(Greenhouse, Lever, Ashby, Workable) from TopStartups.io.

Features:
- Dedicated Bangalore and Remote location filters (?job_location=Bangalore&page=N).
- Extracts direct ATS URLs (job-boards.greenhouse.io, jobs.lever.co, etc.) with zero redirects.
- Extracts official company domains, LinkedIn profile URLs, lead VCs (Sequoia, Accel, YC),
  funding amounts, and valuations.
- Stores jobs in ApplyPilot `jobs` table and upserts startups to `career_watchlist` (is_vip=1).
- Triggers deep email enrichment loop (5-10 verified emails per startup).
"""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup
import httpx

from applypilot.database import (
    get_connection,
    store_jobs,
    store_recruiter_lead,
    upsert_career_watchlist,
)
from applypilot.discovery.bangalore_map_harvester import (
    check_domain_mx,
    enrich_startup_emails_deep,
)

logger = logging.getLogger(__name__)

TOPSTARTUPS_BASE_URL = "https://topstartups.io/jobs/"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

ATS_DOMAIN_KEYWORDS = (
    "greenhouse.io",
    "lever.co",
    "ashbyhq.com",
    "workable.com",
    "smartrecruiters.com",
    "recruitee.com",
    "bamboohr.com",
    "breezy.hr",
    "myworkdayjobs.com",
)


def extract_ats_apply_url(item_soup: BeautifulSoup) -> str | None:
    """Find direct external ATS application link within a job card."""
    for a in item_soup.find_all("a", href=True):
        href = a["href"].strip()
        for ats in ATS_DOMAIN_KEYWORDS:
            if ats in href:
                return href
    return None


def extract_company_website(item_soup: BeautifulSoup) -> str | None:
    """Extract official company website link from topstartups card."""
    for a in item_soup.find_all("a", href=True):
        href = a["href"].strip()
        if "utm_source=topstartups.io" in href:
            parsed = urlparse(href)
            # Remove utm_source query params
            return f"{parsed.scheme}://{parsed.netloc}"
        if href.startswith("http") and not any(
            d in href
            for d in (
                "topstartups.io",
                "linkedin.com",
                "greenhouse.io",
                "lever.co",
                "ashbyhq.com",
                "twitter.com",
                "x.com",
                "airtable.com",
            )
        ):
            parsed = urlparse(href)
            return f"{parsed.scheme}://{parsed.netloc}"
    return None


def extract_company_linkedin(item_soup: BeautifulSoup) -> str | None:
    """Extract company LinkedIn link if present."""
    for a in item_soup.find_all("a", href=True):
        href = a["href"].strip()
        if "linkedin.com/company" in href:
            return href
    return None


def parse_topstartups_card(card_soup: BeautifulSoup) -> dict[str, Any] | None:
    """Parse a single .infinite-item card from TopStartups.io."""
    text_content = card_soup.get_text(separator=" ", strip=True)
    if not text_content:
        return None

    # Title & Company Name extraction:
    # TopStartups cards typically have:
    # <h3><a ...>Title</a></h3> and company name or link
    ats_url = extract_ats_apply_url(card_soup)
    website_url = extract_company_website(card_soup)
    linkedin_url = extract_company_linkedin(card_soup)

    # Find job title
    title = None
    title_el = card_soup.find(["h3", "h4", "h2"])
    if title_el:
        title = title_el.get_text(strip=True)
    if not title:
        # Fallback to ATS link text
        for a in card_soup.find_all("a", href=True):
            if ats_url and a["href"] == ats_url:
                title = a.get_text(strip=True)
                break

    # If title not found or too short
    if not title or len(title) < 2:
        # Heuristic: first strong or bold element
        b_el = card_soup.find(["b", "strong"])
        if b_el:
            title = b_el.get_text(strip=True)

    # Company name extraction:
    # Try finding link before job title or from card links
    company_name = None
    for a in card_soup.find_all("a"):
        href = a.get("href", "")
        if "utm_source=topstartups.io" in href:
            company_name = a.get_text(strip=True)
            if company_name and len(company_name) > 1:
                break

    if not company_name and website_url:
        parsed = urlparse(website_url)
        company_name = parsed.netloc.replace("www.", "").split(".")[0].capitalize()

    if not company_name:
        return None

    domain = None
    if website_url:
        parsed = urlparse(website_url)
        domain = parsed.netloc.lower().replace("www.", "")

    # Extract funding / investors snippet
    funding_info = None
    for m in ["Series", "Seed", "valuation", "Sequoia", "Accel", "Khosla", "a16z", "Y Combinator"]:
        if m in text_content:
            funding_info = text_content[:200]
            break

    return {
        "title": title or "Software Engineer",
        "company_name": company_name,
        "domain": domain,
        "website_url": website_url,
        "apply_url": ats_url or website_url,
        "linkedin_url": linkedin_url,
        "raw_text": text_content,
        "funding_info": funding_info,
        "source": "topstartups",
    }


def scrape_topstartups_page(
    location: str = "Bangalore",
    page: int = 1,
    timeout: float = 15.0,
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """Scrape a single page of TopStartups.io."""
    url = f"{TOPSTARTUPS_BASE_URL}?job_location={location}&page={page}"
    should_close = False
    if client is None:
        client = httpx.Client(headers=DEFAULT_HEADERS, timeout=timeout)
        should_close = True

    results: list[dict[str, Any]] = []
    try:
        resp = client.get(url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        container = soup.find(class_=lambda c: c and "infinite-container" in c)
        if not container:
            return []

        items = container.find_all(class_=lambda c: c and "infinite-item" in c)
        for it in items:
            parsed = parse_topstartups_card(it)
            if parsed:
                results.append(parsed)
    except Exception as exc:
        logger.error("Error scraping TopStartups page %d (%s): %s", page, location, exc)
    finally:
        if should_close:
            client.close()

    return results


def scrape_topstartups_jobs(
    location: str = "Bangalore",
    max_pages: int = 3,
    timeout: float = 15.0,
) -> list[dict[str, Any]]:
    """Scrape multiple pages of TopStartups jobs for a location (e.g. Bangalore, Remote)."""
    all_jobs: list[dict[str, Any]] = []
    with httpx.Client(headers=DEFAULT_HEADERS, timeout=timeout) as client:
        for p in range(1, max_pages + 1):
            page_jobs = scrape_topstartups_page(location=location, page=p, client=client)
            if not page_jobs:
                break
            all_jobs.extend(page_jobs)

    logger.info("Scraped %d jobs across %d pages from TopStartups (%s)", len(all_jobs), max_pages, location)
    return all_jobs


def ingest_topstartups_to_db(
    jobs_data: list[dict[str, Any]],
    enrich_emails: bool = True,
    target_emails_per_startup: int = 6,
    conn: Any = None,
) -> dict[str, int]:
    """Ingest scraped TopStartups jobs and companies into SQLite database."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    stats = {
        "jobs_stored": 0,
        "companies_ingested": 0,
        "emails_enriched": 0,
        "leads_created": 0,
        "domains_verified": 0,
    }

    try:
        # Group jobs by company
        by_company: dict[str, list[dict[str, Any]]] = {}
        for j in jobs_data:
            cname = j["company_name"]
            by_company.setdefault(cname, []).append(j)

        for cname, c_jobs in by_company.items():
            first_job = c_jobs[0]
            domain = first_job.get("domain")
            website = first_job.get("website_url")
            linkedin_url = first_job.get("linkedin_url")
            notes = first_job.get("funding_info") or "TopStartups VC-backed"

            # 1. Upsert company to career_watchlist as VIP Tier 1
            upsert_career_watchlist(
                company_name=cname,
                official_domain=domain,
                careers_page_url=website,
                ats_provider=None,
                ats_board_token=None,
                priority_tier=1,
                is_vip=1,
                total_funding=notes[:100] if notes else None,
                conn=conn,
            )
            stats["companies_ingested"] += 1

            # 2. Store jobs in ApplyPilot jobs table
            db_jobs = []
            for j in c_jobs:
                db_jobs.append({
                    "title": j["title"],
                    "company": cname,
                    "url": j["apply_url"],
                    "location": "Bengaluru / Remote",
                    "description": j.get("raw_text", "")[:400],
                    "department": "Engineering / Product",
                })
            stored_res = store_jobs(conn, db_jobs, site="topstartups", strategy="topstartups_scraper")
            new_cnt = stored_res[0] if isinstance(stored_res, tuple) else (stored_res or 0)
            stats["jobs_stored"] += new_cnt
            for j in db_jobs:
                conn.execute("UPDATE jobs SET company = ? WHERE url = ?", (cname, j["url"]))

            # 3. Deep Email Enrichment Loop
            if enrich_emails and domain:
                mx_ok = check_domain_mx(domain)
                if mx_ok:
                    stats["domains_verified"] += 1
                    leads = enrich_startup_emails_deep(
                        company_name=cname,
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
                                role_title=f"{'Founder / Executive' if c_type == 'founder' else 'Talent / Recruitment'} at {cname}",
                                company_name=cname,
                                company_domain=domain,
                                contact_name=l.get("contact_name") or f"{cname} Talent",
                                contact_linkedin_url=linkedin_url,
                                contact_type=c_type,
                                source_platform="topstartups.io",
                                source_post_url=first_job.get("apply_url"),
                                evidence_snippet=notes or f"Newly funded startup {cname}",
                                execution_route="DUAL_ATTACK" if first_job.get("apply_url") else "EMAIL_ONLY",
                                conn=conn,
                            )
                            stats["leads_created"] += 1
                        except Exception:
                            pass
        conn.commit()
    finally:
        if should_close:
            conn.close()

    logger.info("TopStartups ingestion complete: %s", stats)
    return stats
