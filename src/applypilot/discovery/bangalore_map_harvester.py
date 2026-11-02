"""Bangalore Startup Map Harvester & VIP 500 Contact Enricher.

Extracts all 1,085+ startups, 132+ actively hiring companies, and 6,400+ live jobs
directly from bangalorestartupmap.com Next.js React Server Components stream
(self.__next_f.push(...)) and individual company profiles (/company/[slug]).

Enriches each company with:
- Founder names + direct personal LinkedIn profile URLs
- Generated 280-char personalized LinkedIn connection notes (<=300 char LinkedIn limit)
- Careers portals, ATS links (Greenhouse, Lever, Ashby, Freshteam, Zoho Recruit)
- Scraped / verified HR and founder emails (careers@, hr@, talent@, hello@)
- Populates career_watchlist (priority_tier=1, is_vip=1) and recruiter_leads.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from applypilot.core.regex_patterns import EMAIL_COMPILED_PATTERN
from applypilot.database import (
    get_connection,
    store_jobs,
    store_recruiter_lead,
    upsert_career_watchlist,
)

logger = logging.getLogger(__name__)

MAP_URL = "https://www.bangalorestartupmap.com/"
COMPANY_BASE_URL = "https://www.bangalorestartupmap.com/company/"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

ATS_URL_PATTERN = re.compile(
    r"https?://[a-zA-Z0-9.-]*(?:greenhouse\.io|lever\.co|ashbyhq\.com|workday\.com|"
    r"myworkdayjobs\.com|workable\.com|freshteam\.com|zohorecruit\.[a-z]+|"
    r"bamboohr\.com|breezy\.hr|recruitee\.com)[^\s\"<>']*",
    re.IGNORECASE,
)

LINKEDIN_PROFILE_PATTERN = re.compile(
    r"https?://(?:[a-z]{2}\.)?linkedin\.com/in/[a-zA-Z0-9_.-]+",
    re.IGNORECASE,
)

LINKEDIN_COMPANY_PATTERN = re.compile(
    r"https?://(?:[a-z]{2}\.)?linkedin\.com/company/[a-zA-Z0-9_.-]+",
    re.IGNORECASE,
)


def _clean_val(val: Any) -> Any:
    """Clean Next.js undefined values and strip strings."""
    if val is None or val == "$undefined":
        return None
    if isinstance(val, str):
        val = val.strip()
        return val if val else None
    return val


def fetch_bangalore_map_raw(url: str = MAP_URL, timeout: float = 25.0) -> str:
    """Fetch raw HTML from bangalorestartupmap.com."""
    with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=timeout) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text


def parse_bangalore_map_rsc(html: str) -> tuple[list[dict], dict[str, list], dict[str, list]]:
    """Parse Next.js React Server Components stream for startups, roles, and roleKeywords.

    Returns:
        (startups_list, roles_by_slug_dict, role_keywords_by_slug_dict)
    """
    pushes = re.findall(r'self\.__next_f\.push\(\[1,\s*"(.*?)"\]\)', html, re.DOTALL)
    if not pushes:
        # Fallback: try finding unescaped payload or script chunks
        logger.warning("No self.__next_f.push chunks found in HTML")
        return [], {}, {}

    target_chunk = None
    for p in reversed(pushes):
        if "startups" in p and ("roles" in p or "stage" in p):
            target_chunk = p
            break

    if not target_chunk:
        logger.warning("No push chunk with startups found")
        return [], {}, {}

    try:
        unescaped = target_chunk.encode("utf-8").decode("unicode_escape")
    except Exception as e:
        logger.error("Failed to unescape RSC push chunk: %s", e)
        return [], {}, {}

    decoder = json.JSONDecoder()
    startups: list[dict] = []
    roles: dict[str, list] = {}
    role_keywords: dict[str, list] = {}

    # 1. Parse startups array
    idx_startups = unescaped.find('"startups":')
    if idx_startups != -1:
        try:
            start_pos = idx_startups + len('"startups":')
            raw_startups, _ = decoder.raw_decode(unescaped[start_pos:])
            if isinstance(raw_startups, list):
                for s in raw_startups:
                    if isinstance(s, dict):
                        # Clean fields
                        cleaned = {k: _clean_val(v) for k, v in s.items()}
                        startups.append(cleaned)
        except Exception as e:
            logger.error("Failed to decode startups array: %s", e)

    # 2. Parse roles map
    idx_roles = unescaped.find('"roles":')
    if idx_roles != -1:
        try:
            start_pos = idx_roles + len('"roles":')
            raw_roles, _ = decoder.raw_decode(unescaped[start_pos:])
            if isinstance(raw_roles, dict):
                roles = raw_roles
        except Exception as e:
            logger.debug("Failed to decode roles map: %s", e)

    # 3. Parse roleKeywords map
    idx_kw = unescaped.find('"roleKeywords":')
    if idx_kw != -1:
        try:
            start_pos = idx_kw + len('"roleKeywords":')
            raw_kw, _ = decoder.raw_decode(unescaped[start_pos:])
            if isinstance(raw_kw, dict):
                role_keywords = raw_kw
        except Exception as e:
            logger.debug("Failed to decode roleKeywords map: %s", e)

    # Attach open role metadata to startups
    for s in startups:
        slug = s.get("slug")
        if slug and slug in roles:
            s["open_roles"] = roles[slug]
            s["open_roles_count"] = len(roles[slug])
            s["is_hiring"] = True
        else:
            s["open_roles"] = []
            s["open_roles_count"] = 0
            s["is_hiring"] = False

        if slug and slug in role_keywords:
            s["role_keywords"] = role_keywords[slug]
        else:
            s["role_keywords"] = []

    return startups, roles, role_keywords


def fetch_company_deep_profile(
    slug: str,
    client: httpx.Client | None = None,
    timeout: float = 12.0,
) -> dict[str, Any]:
    """Fetch /company/[slug] to extract direct ATS links, website, and founder LinkedIn URLs."""
    url = f"{COMPANY_BASE_URL}{slug}"
    should_close = False
    if client is None:
        client = httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=timeout)
        should_close = True

    result: dict[str, Any] = {
        "slug": slug,
        "profile_url": url,
        "website": None,
        "ats_links": [],
        "company_linkedin": None,
        "founder_linkedins": [],
        "careers_url": None,
    }

    try:
        resp = client.get(url)
        if resp.status_code != 200:
            return result
        html = resp.text

        # Extract JSON-LD Organization data
        json_ld_blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
        for block in json_ld_blocks:
            try:
                data = json.loads(block)
                if isinstance(data, dict):
                    if data.get("@type") == "Organization":
                        if data.get("url"):
                            result["website"] = data["url"]
            except Exception:
                pass

        # Extract external links
        hrefs = re.findall(r'href="([^"]+)"', html)
        seen_ats = set()
        seen_founder_li = set()

        for href in hrefs:
            # ATS links
            if ATS_URL_PATTERN.search(href):
                clean_href = href.split("?")[0] if "google.com" not in href else href
                if clean_href not in seen_ats:
                    seen_ats.add(clean_href)
                    result["ats_links"].append(href)

            # Company LinkedIn
            if LINKEDIN_COMPANY_PATTERN.search(href) and not result["company_linkedin"]:
                result["company_linkedin"] = href

            # Founder LinkedIn
            if LINKEDIN_PROFILE_PATTERN.search(href):
                clean_li = href.split("?")[0]
                if clean_li not in seen_founder_li:
                    seen_founder_li.add(clean_li)
                    result["founder_linkedins"].append(clean_li)

            # Direct careers page
            if any(k in href.lower() for k in ["/careers", "/jobs", "careers.", "jobs."]) and "google.com" not in href:
                if not result["careers_url"] and not href.startswith("/"):
                    result["careers_url"] = href

    except Exception as e:
        logger.debug("Error fetching company deep profile for %s: %s", slug, e)
    finally:
        if should_close:
            client.close()

    return result


def generate_linkedin_connection_note(
    founder_name: str,
    startup_name: str,
    sector: str | None = None,
    tagline: str | None = None,
) -> str:
    """Generate a crisp, high-conversion personalized LinkedIn connection note.

    Strictly stays within LinkedIn's 300-character invite limit (target <= 280 chars).
    """
    clean_founder = (founder_name or "").strip()
    first_name = clean_founder.split()[0] if clean_founder else "there"
    clean_startup = (startup_name or "").strip()
    clean_sector = (sector or "").strip()

    if clean_sector and clean_sector.lower() not in ["other", "$undefined"]:
        base_note = (
            f"Hi {first_name}, impressed by what you're building at {clean_startup} in {clean_sector}! "
            f"As a software engineer following Bangalore's startup ecosystem, I'd love to connect and follow your journey."
        )
    elif tagline:
        short_tag = tagline[:60].strip().rstrip(".")
        base_note = (
            f"Hi {first_name}, saw your work at {clean_startup} ({short_tag}). "
            f"As a developer passionate about high-impact tech, I'd love to connect and keep in touch."
        )
    else:
        base_note = (
            f"Hi {first_name}, really admire what the team is creating at {clean_startup}. "
            f"As a software engineer following your journey, I'd love to connect and follow your updates."
        )

    # Ensure <= 280 characters
    if len(base_note) > 280:
        base_note = base_note[:277] + "..."

    return base_note


def enrich_startup_website_emails(
    website_url: str,
    client: httpx.Client | None = None,
    timeout: float = 6.0,
) -> list[str]:
    """Crawl company website and /careers page to extract published hiring emails."""
    if not website_url or not website_url.startswith("http"):
        return []

    should_close = False
    if client is None:
        client = httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=timeout)
        should_close = True

    emails: set[str] = set()
    parsed = urlparse(website_url)
    domain = parsed.netloc.lower().replace("www.", "")
    base_origin = f"{parsed.scheme}://{parsed.netloc}"

    pages_to_check = [website_url]
    for sub in ["/careers", "/about", "/contact", "/jobs"]:
        pages_to_check.append(f"{base_origin}{sub}")

    try:
        for page_url in pages_to_check:
            try:
                resp = client.get(page_url)
                if resp.status_code == 200:
                    found = EMAIL_COMPILED_PATTERN.findall(resp.text)
                    for em in found:
                        em_clean = em.lower().strip()
                        # Exclude asset or invalid domains
                        if not any(em_clean.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".svg", ".gif"]):
                            if not any(noise in em_clean for noise in ["example.com", "sentry.io", "wix.com"]):
                                emails.add(em_clean)
                if emails:
                    # Once we found emails from careers/root, we don't need to probe every path
                    break
            except Exception:
                continue
    finally:
        if should_close:
            client.close()

    # Sort prioritizing careers, hr, talent, founder
    priority_order = ["careers@", "jobs@", "talent@", "hr@", "founder@", "team@", "hello@"]

    def _sort_key(e: str) -> int:
        for i, prefix in enumerate(priority_order):
            if prefix in e:
                return i
        return 99

    sorted_emails = sorted(list(emails), key=_sort_key)
    return sorted_emails


def import_bangalore_startups_to_watchlist(
    sectors: list[str] | None = None,
    only_hiring: bool = False,
    limit: int = 50,
    fetch_deep: bool = True,
    dry_run: bool = False,
    conn=None,
) -> dict[str, Any]:
    """Import startups from Bangalore Startup Map into career_watchlist (VIP Top 500) and recruiter_leads.

    Args:
        sectors: Target sector filter (e.g. ['AI', 'SaaS', 'Fintech', 'Deeptech'])
        only_hiring: If True, only import startups with open roles on the map
        limit: Max startups to process
        fetch_deep: If True, crawl individual /company/[slug] for ATS URLs and founder LinkedIn links
        dry_run: If True, return extracted data without modifying DB
        conn: Optional SQLite connection
    """
    logger.info("Fetching Bangalore Startup Map RSC payload...")
    html = fetch_bangalore_map_raw()
    startups, roles, role_keywords = parse_bangalore_map_rsc(html)

    if not startups:
        return {
            "status": "error",
            "message": "Failed to parse startups from Bangalore Startup Map RSC stream",
            "imported_companies": 0,
        }

    # Normalize sectors filter
    target_sectors = [s.lower().strip() for s in sectors] if sectors else []

    filtered: list[dict] = []
    for s in startups:
        # Check hiring filter
        if only_hiring and not s.get("is_hiring"):
            continue

        # Check sector filter
        sec = (s.get("sector") or "").lower()
        tags = [str(t).lower() for t in s.get("tags") or []]
        if target_sectors:
            matched_sector = any(
                ts in sec or any(ts in tag for tag in tags) for ts in target_sectors
            )
            if not matched_sector:
                continue

        filtered.append(s)

    selected = filtered[:limit]
    logger.info("Selected %d / %d startups matching criteria", len(selected), len(startups))

    if conn is None and not dry_run:
        conn = get_connection()

    imported_companies = 0
    open_roles_indexed = 0
    recruiter_leads_created = 0
    companies_summary: list[dict] = []

    with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=12.0) as client:
        for idx, s in enumerate(selected):
            name = s.get("name") or "Unknown Startup"
            slug = s.get("slug") or name.lower().replace(" ", "-")
            sector = s.get("sector")
            stage = s.get("stage")
            area = s.get("area")
            location = s.get("hsr_location") or area
            website = s.get("website")
            tagline = s.get("tagline")
            founders_raw = s.get("founders")
            founder_links = s.get("founder_links") or []

            # Deep profile fetch for ATS links, direct URLs, and founder LinkedIn links
            deep_ats_links = []
            deep_founder_li = []
            deep_careers_url = None
            company_linkedin = None

            if fetch_deep:
                deep = fetch_company_deep_profile(slug, client=client)
                deep_ats_links = deep.get("ats_links", [])
                deep_founder_li = deep.get("founder_linkedins", [])
                deep_careers_url = deep.get("careers_url")
                company_linkedin = deep.get("company_linkedin")
                if not website and deep.get("website"):
                    website = deep["website"]

            # Merge founder LinkedIn URLs
            all_founder_linkedins = list(deep_founder_li)
            if isinstance(founder_links, list):
                for fl in founder_links:
                    if isinstance(fl, dict) and fl.get("url"):
                        u = fl["url"]
                        if "linkedin.com/in/" in u and u not in all_founder_linkedins:
                            all_founder_linkedins.append(u)
                    elif isinstance(fl, str) and "linkedin.com/in/" in fl and fl not in all_founder_linkedins:
                        all_founder_linkedins.append(fl)

            # Discover / enrich emails
            discovered_emails: list[str] = []
            if website:
                try:
                    discovered_emails = enrich_startup_website_emails(website, client=client)
                except Exception as e:
                    logger.debug("Email crawl error for %s: %s", website, e)

            # Detect ATS provider
            detected_ats = None
            primary_careers_url = deep_careers_url
            if deep_ats_links:
                first_ats = deep_ats_links[0]
                primary_careers_url = first_ats
                if "greenhouse.io" in first_ats:
                    detected_ats = "greenhouse"
                elif "lever.co" in first_ats:
                    detected_ats = "lever"
                elif "ashbyhq.com" in first_ats:
                    detected_ats = "ashby"
                elif "workday" in first_ats:
                    detected_ats = "workday"
                elif "workable.com" in first_ats:
                    detected_ats = "workable"
                elif "freshteam.com" in first_ats:
                    detected_ats = "freshteam"
                elif "zohorecruit" in first_ats:
                    detected_ats = "zohorecruit"

            domain = None
            if website:
                try:
                    domain = urlparse(website).netloc.lower().replace("www.", "")
                except Exception:
                    pass

            open_roles_count = s.get("open_roles_count", 0) + len(deep_ats_links)

            # Founders JSON structure
            founders_record = {
                "names": founders_raw,
                "linkedin_urls": all_founder_linkedins,
                "founder_links": founder_links,
            }

            company_data = {
                "name": name,
                "slug": slug,
                "sector": sector,
                "stage": stage,
                "area": area,
                "website": website,
                "domain": domain,
                "careers_url": primary_careers_url,
                "ats_provider": detected_ats,
                "open_roles_count": open_roles_count,
                "emails": discovered_emails,
                "founder_linkedins": all_founder_linkedins,
                "company_linkedin": company_linkedin,
            }
            companies_summary.append(company_data)

            if dry_run:
                continue

            # 1. Upsert into career_watchlist as VIP 500 (priority_tier=1, is_vip=1)
            cid = upsert_career_watchlist(
                company_name=name,
                official_domain=domain,
                careers_page_url=primary_careers_url,
                ats_provider=detected_ats,
                slug=slug,
                priority_tier=1,
                is_vip=1,
                stage=stage,
                sector=sector,
                area=area,
                location=location,
                founders_json=json.dumps(founders_record),
                hr_contacts_json=json.dumps(discovered_emails),
                open_roles_count=open_roles_count,
                conn=conn,
            )
            imported_companies += 1

            # 2. Store open roles into jobs table
            for ats_url in deep_ats_links:
                role_title = f"Open Role at {name}"
                # If ATS URL has a role title slug, format it nicely
                parsed_path = urlparse(ats_url).path.strip("/").split("/")
                if len(parsed_path) >= 2:
                    potential_slug = parsed_path[-1].replace("-", " ").replace("_", " ").title()
                    if len(potential_slug) > 3 and not potential_slug.isdigit():
                        role_title = potential_slug

                try:
                    route = "DUAL_ATTACK" if discovered_emails or all_founder_linkedins else "PORTAL_ONLY"
                    new_cnt, _ = store_jobs(
                        conn=conn,
                        jobs=[{
                            "url": ats_url,
                            "title": role_title,
                            "location": location or "Bengaluru, India",
                        }],
                        site="bangalorestartupmap.com",
                        strategy="bangalore_map_harvester",
                    )
                    conn.execute(
                        "UPDATE jobs SET company = ?, execution_route = ? WHERE url = ?",
                        (name, route, ats_url),
                    )
                    conn.commit()
                    if new_cnt > 0:
                        open_roles_indexed += 1
                except Exception as e:
                    logger.debug("Job already stored or insert skipped: %s", e)

            # 3. Create recruiter_leads for discovered HR emails and founder LinkedIn profiles
            # A) For discovered emails:
            for email in discovered_emails:
                try:
                    store_recruiter_lead(
                        contact_email=email,
                        role_title=f"Engineer / Talent at {name}",
                        company_name=name,
                        company_domain=domain,
                        contact_name=None,
                        contact_type="recruiter" if "hr" in email or "talent" in email or "careers" in email else "founder",
                        source_platform="bangalorestartupmap.com",
                        source_post_url=f"{COMPANY_BASE_URL}{slug}",
                        evidence_snippet=tagline or f"{name} is an active startup in {area or 'Bengaluru'}",
                        execution_route="DUAL_ATTACK" if primary_careers_url else "EMAIL_ONLY",
                        conn=conn,
                    )
                    recruiter_leads_created += 1
                except Exception as e:
                    logger.debug("Lead store skipped: %s", e)

            # B) For discovered founder LinkedIn URLs:
            for founder_li in all_founder_linkedins:
                # Deduce founder name from founders_raw or URL
                founder_display_name = founders_raw if isinstance(founders_raw, str) else "Founder"
                if "," in str(founder_display_name):
                    founder_display_name = str(founder_display_name).split(",")[0].strip()

                note = generate_linkedin_connection_note(
                    founder_name=founder_display_name,
                    startup_name=name,
                    sector=sector,
                    tagline=tagline,
                )

                dummy_email = f"linkedin-{slug}-{hash(founder_li) % 10000}@connect.linkedin.com"
                try:
                    store_recruiter_lead(
                        contact_email=dummy_email,
                        role_title=f"Founder / Leadership at {name}",
                        company_name=name,
                        company_domain=domain,
                        contact_name=founder_display_name,
                        contact_linkedin_url=founder_li,
                        linkedin_connection_note=note,
                        contact_type="founder",
                        source_platform="bangalorestartupmap.com",
                        source_post_url=founder_li,
                        evidence_snippet=f"Founder of {name} ({stage or 'Funded'}, {sector or 'Tech'}). {tagline or ''}",
                        execution_route="DUAL_ATTACK" if primary_careers_url else "EMAIL_ONLY",
                        conn=conn,
                    )
                    recruiter_leads_created += 1
                except Exception as e:
                    logger.debug("Founder lead store skipped: %s", e)

    return {
        "status": "success",
        "total_startups_on_map": len(startups),
        "matching_startups_found": len(filtered),
        "imported_companies": imported_companies if not dry_run else len(selected),
        "open_roles_indexed": open_roles_indexed,
        "recruiter_leads_created": recruiter_leads_created,
        "companies": companies_summary,
    }
