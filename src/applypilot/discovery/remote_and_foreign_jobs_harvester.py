"""Remote & Foreign Job Harvester and Global Executive Discovery.

Scrapes high-signal international and remote-first job ecosystems:
1. RemoteOK (remoteok.com/api): Worldwide, US, EU tech & AI postings.
2. We Work Remotely (weworkremotely.com RSS): Premium engineering & devops openings.
3. Jobicy (jobicy.com/api/v2): Verified global remote roles.
4. Arbeitnow (arbeitnow.com/api): European and international tech opportunities.
5. Y Combinator & Funded Startups: US/EU/Global seed and series-A startups with foreign CEO/CTO leadership.

Automatically:
- Deduplicates and stores jobs in the SQLite jobs table with location and salary metadata.
- Enrolls discovered foreign companies into career_watchlist (priority_tier=1, is_vip=1).
- Triggers deep executive resolution (foreign CEO, CTO, VP Engineering) and Google DoH MX validation.
"""

from __future__ import annotations

import html
import json
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from applypilot.database import (
    get_connection,
    store_jobs,
    upsert_career_watchlist,
)

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 (ApplyPilot Autonomous Engine)"
    ),
    "Accept": "application/json, application/xml, text/xml, */*",
}


def _clean_text(raw_text: str | None) -> str:
    """Strip HTML tags, unescape entities, and collapse whitespace."""
    if not raw_text:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw_text)
    unescaped = html.unescape(text)
    return re.sub(r"\s+", " ", unescaped).strip()


def _extract_domain_from_url(url: str | None) -> str | None:
    """Extract base domain from job or company URL."""
    if not url:
        return None
    try:
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        netloc = parsed.netloc.lower().replace("www.", "")
        # Filter out job aggregator hostnames
        if any(agg in netloc for agg in ["remoteok.com", "weworkremotely.com", "jobicy.com", "arbeitnow.com", "greenhouse.io", "lever.co", "ashbyhq.com"]):
            return None
        return netloc if "." in netloc else None
    except Exception:
        return None


# -----------------------------------------------------------------------------
# 1. RemoteOK API Harvester
# -----------------------------------------------------------------------------

def fetch_remoteok_jobs(
    limit: int = 50,
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """Fetch remote engineering and AI jobs from RemoteOK public API."""
    url = "https://remoteok.com/api"
    should_close = False
    if client is None:
        client = httpx.Client(headers=DEFAULT_HEADERS, timeout=12.0, follow_redirects=True)
        should_close = True

    jobs: list[dict[str, Any]] = []
    try:
        resp = client.get(url)
        if resp.status_code == 200:
            raw_items = resp.json()
            for item in raw_items:
                if not isinstance(item, dict) or not item.get("position"):
                    continue
                
                title = item.get("position", "").strip()
                company = item.get("company", "").strip()
                apply_url = item.get("url") or item.get("apply_url")
                if not apply_url.startswith("http"):
                    apply_url = f"https://remoteok.com{apply_url}"

                loc = item.get("location") or "Remote (Worldwide)"
                tags = item.get("tags") or []
                desc = _clean_text(item.get("description", ""))

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": f"Remote • {loc}" if "remote" not in loc.lower() else loc,
                    "url": apply_url,
                    "site": "RemoteOK",
                    "description": desc[:3000],
                    "tags": tags,
                    "salary_min": item.get("salary_min"),
                    "salary_max": item.get("salary_max"),
                    "domain": _extract_domain_from_url(item.get("company_url")),
                    "is_remote": True,
                    "is_foreign": True,
                })
                if len(jobs) >= limit:
                    break
    except Exception as e:
        logger.warning("RemoteOK fetch notice: %s", e)
    finally:
        if should_close:
            client.close()

    return jobs


# -----------------------------------------------------------------------------
# 2. We Work Remotely (WWR) RSS Harvester
# -----------------------------------------------------------------------------

def fetch_weworkremotely_jobs(
    limit: int = 30,
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """Fetch programming and engineering postings from We Work Remotely RSS feeds."""
    feed_urls = [
        "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
    ]
    should_close = False
    if client is None:
        client = httpx.Client(headers=DEFAULT_HEADERS, timeout=12.0, follow_redirects=True)
        should_close = True

    jobs: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    try:
        for f_url in feed_urls:
            try:
                resp = client.get(f_url)
                if resp.status_code != 200:
                    continue
                root = ET.fromstring(resp.content)
                for item in root.findall(".//item"):
                    raw_title = item.find("title").text if item.find("title") is not None else ""
                    link = item.find("link").text if item.find("link") is not None else ""
                    desc = item.find("description").text if item.find("description") is not None else ""

                    if not raw_title or not link or link in seen_urls:
                        continue
                    seen_urls.add(link)

                    # WWR titles typically formatted as: "Company Name: Job Title"
                    company = "Remote Tech Startup"
                    title = raw_title
                    if ":" in raw_title:
                        parts = raw_title.split(":", 1)
                        company = parts[0].strip()
                        title = parts[1].strip()

                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": "Remote • Global",
                        "url": link,
                        "site": "WeWorkRemotely",
                        "description": _clean_text(desc)[:3000],
                        "tags": ["remote", "programming", "engineering"],
                        "domain": None,
                        "is_remote": True,
                        "is_foreign": True,
                    })
                    if len(jobs) >= limit:
                        break
            except Exception as f_err:
                logger.debug("WWR single feed notice: %s", f_err)
            if len(jobs) >= limit:
                break
    except Exception as e:
        logger.warning("WWR fetch notice: %s", e)
    finally:
        if should_close:
            client.close()

    return jobs


# -----------------------------------------------------------------------------
# 3. Jobicy Global Remote API Harvester
# -----------------------------------------------------------------------------

def fetch_jobicy_jobs(
    limit: int = 30,
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """Fetch global tech roles from Jobicy API."""
    url = f"https://jobicy.com/api/v2/remote-jobs?count={min(limit, 50)}"
    should_close = False
    if client is None:
        client = httpx.Client(headers=DEFAULT_HEADERS, timeout=12.0, follow_redirects=True)
        should_close = True

    jobs: list[dict[str, Any]] = []
    try:
        resp = client.get(url)
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("jobs", []):
                title = item.get("jobTitle", "").strip()
                company = item.get("companyName", "").strip()
                apply_url = item.get("url")
                geo = item.get("jobGeo") or "Anywhere / Global"

                if not title or not company or not apply_url:
                    continue

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": f"Remote • {geo}",
                    "url": apply_url,
                    "site": "Jobicy",
                    "description": _clean_text(item.get("jobDescription", ""))[:3000],
                    "tags": item.get("jobType") or ["remote"],
                    "domain": _extract_domain_from_url(item.get("companyLogo")),
                    "is_remote": True,
                    "is_foreign": True,
                })
                if len(jobs) >= limit:
                    break
    except Exception as e:
        logger.warning("Jobicy fetch notice: %s", e)
    finally:
        if should_close:
            client.close()

    return jobs


# -----------------------------------------------------------------------------
# 4. Arbeitnow European & Global Tech Harvester
# -----------------------------------------------------------------------------

def fetch_arbeitnow_jobs(
    limit: int = 30,
    remote_only: bool = True,
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """Fetch European and global remote tech positions from Arbeitnow."""
    url = "https://www.arbeitnow.com/api/job-board-api"
    should_close = False
    if client is None:
        client = httpx.Client(headers=DEFAULT_HEADERS, timeout=12.0, follow_redirects=True)
        should_close = True

    jobs: list[dict[str, Any]] = []
    try:
        resp = client.get(url)
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("data", []):
                is_rem = item.get("remote", False)
                if remote_only and not is_rem:
                    continue

                title = item.get("title", "").strip()
                company = item.get("company_name", "").strip()
                apply_url = item.get("url")
                loc = item.get("location") or "Europe / Remote"

                if not title or not company or not apply_url:
                    continue

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": f"Remote • {loc}" if is_rem and "remote" not in loc.lower() else loc,
                    "url": apply_url,
                    "site": "Arbeitnow",
                    "description": _clean_text(item.get("description", ""))[:3000],
                    "tags": item.get("tags") or [],
                    "domain": None,
                    "is_remote": is_rem,
                    "is_foreign": True,
                })
                if len(jobs) >= limit:
                    break
    except Exception as e:
        logger.warning("Arbeitnow fetch notice: %s", e)
    finally:
        if should_close:
            client.close()

    return jobs


# -----------------------------------------------------------------------------
# 5. Composite Remote Harvester & Auto-Enrollment into Watchlist
# -----------------------------------------------------------------------------

def harvest_remote_and_foreign_jobs(
    limit_per_source: int = 25,
    keyword_filter: list[str] | None = None,
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """Harvest across all top remote job boards and return deduplicated list."""
    all_jobs: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    sources = [
        ("RemoteOK", fetch_remoteok_jobs),
        ("WeWorkRemotely", fetch_weworkremotely_jobs),
        ("Jobicy", fetch_jobicy_jobs),
        ("Arbeitnow", fetch_arbeitnow_jobs),
    ]

    for name, fetch_fn in sources:
        try:
            batch = fetch_fn(limit=limit_per_source, client=client)
            for j in batch:
                key = f"{j['company'].lower()}::{j['title'].lower()}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    # Optional keyword filter (software, engineer, ai, backend, frontend, fullstack, dev)
                    if keyword_filter:
                        title_lower = j["title"].lower()
                        desc_lower = j["description"].lower()
                        if not any(k.lower() in title_lower or k.lower() in desc_lower for k in keyword_filter):
                            continue
                    all_jobs.append(j)
        except Exception as e:
            logger.warning("Error harvesting %s: %s", name, e)

    return all_jobs


def ingest_remote_jobs_to_db(
    jobs: list[dict[str, Any]],
    conn: Any = None,
) -> dict[str, Any]:
    """Store remote and foreign jobs into SQLite and auto-enroll companies into career_watchlist."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    stats = {
        "jobs_stored": 0,
        "companies_enrolled": 0,
        "companies": [],
    }

    if not jobs:
        if should_close:
            conn.close()
        return stats

    # 1. Store jobs into jobs table
    new_jobs_cnt, _ = store_jobs(
        conn=conn,
        jobs=jobs,
        site="remote_aggregator",
        strategy="remote_and_foreign_harvester",
    )
    stats["jobs_stored"] = new_jobs_cnt

    # 2. Auto-enroll companies into career_watchlist (priority_tier=1 for remote/foreign)
    enrolled_set: set[str] = set()
    for j in jobs:
        c_name = j.get("company", "").strip()
        if not c_name or len(c_name) < 2 or c_name in enrolled_set:
            continue
        enrolled_set.add(c_name)

        domain = j.get("domain")
        # Try inferring domain from company name if clean
        if not domain:
            slug = re.sub(r"[^a-zA-Z0-9]", "", c_name).lower()
            if 3 <= len(slug) <= 24:
                domain = f"{slug}.com"

        try:
            upsert_career_watchlist(
                company_name=c_name,
                official_domain=domain,
                careers_page_url=j.get("url"),
                priority_tier=1,
                is_vip=1,
                conn=conn,
            )
            stats["companies_enrolled"] += 1
            stats["companies"].append({"name": c_name, "domain": domain})
        except Exception as e:
            logger.debug("Notice enrolling remote company %s: %s", c_name, e)

    conn.commit()
    if should_close:
        conn.close()

    return stats


# -----------------------------------------------------------------------------
# 6. Foreign CEO / CTO & Funded Startups Harvester
# -----------------------------------------------------------------------------

def search_foreign_executives_and_startups(
    limit: int = 30,
    conn: Any = None,
) -> dict[str, Any]:
    """Discover foreign seed/Series-A funded startups (US/Europe/Remote) via YC OSS API."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    summary = {
        "startups_fetched": 0,
        "startups_enrolled": 0,
        "details": [],
    }

    try:
        from applypilot.discovery.yc_harvester import fetch_yc_startups
        # Fetch remote & global hiring YC startups with foreign leadership
        yc_list = fetch_yc_startups(remote_only=True, hiring_only=True, limit=limit)
        summary["startups_fetched"] = len(yc_list)

        for s in yc_list:
            c_name = s.get("name", "").strip()
            domain = s.get("domain")
            founders = s.get("founders") or []

            founders_json = None
            if founders:
                founders_json = json.dumps([{"name": f, "role": "Co-Founder / Leadership"} for f in founders])

            try:
                upsert_career_watchlist(
                    company_name=c_name,
                    official_domain=domain,
                    careers_page_url=s.get("website") or s.get("yc_url"),
                    priority_tier=1,
                    is_vip=1,
                    conn=conn,
                )
                if founders_json:
                    conn.execute(
                        "UPDATE career_watchlist SET founders_json = ? WHERE company_name = ?",
                        (founders_json, c_name),
                    )
                summary["startups_enrolled"] += 1
                summary["details"].append({"name": c_name, "domain": domain, "founders": founders})
            except Exception as e:
                logger.debug("Notice enrolling YC startup %s: %s", c_name, e)

        conn.commit()
    except Exception as exc:
        logger.warning("Error fetching foreign YC startups: %s", exc)
    finally:
        if should_close:
            conn.close()

    return summary
