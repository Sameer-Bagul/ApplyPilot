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
from applypilot.career_resolver.resolver import resolve_company_career_page
from applypilot.database import commit_with_retry, get_connection, store_jobs, store_recruiter_lead
from applypilot.discovery.email_hunter import (
    clean_domain,
    check_domain_mx_provider,
)
from applypilot.discovery.url_normalize import canonicalize_application_url
from applypilot.learning.migrations import _clean_domain_token, is_aggregator_or_ats_domain
from applypilot.social_discovery.extractor import extract_ats_urls

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data-we-can-use"

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


_AI_SDE_TITLE_RE = re.compile(
    r"\b("
    r"engineer(?:ing)?|developer|programmer|coder|sde\b|sde[-\s]?[123i]|"
    r"ai|ml|machine\s+learning|deep\s+learning|nlp|llm|gen\s*ai|generative\s+ai|"
    r"ai\s+agent|agentic|applied\s+scientist|research\s+scientist|data\s+scientist|"
    r"data\s+engineer|analytics\s+engineer|backend|front[-\s]?end|full[-\s]?stack|"
    r"software|devops|sre|site\s+reliability|mlops|aiops|cloud|infrastructure|"
    r"platform|systems|architect|computer\s+vision|swe|mts|member\s+of\s+technical\s+staff"
    r")\b",
    re.IGNORECASE,
)
_CORE_ENG_RE = re.compile(
    r"\b(engineer|developer|programmer|sde|swe|mts|scientist|architect|devops|sre|mlops)\b",
    re.IGNORECASE,
)
_NON_TECH_TITLE_RE = re.compile(
    r"\b(accountant|accounting|paralegal|legal|counsel|attorney|recruiter|recruiting|"
    r"talent\s+acquisition|account\s+executive|sales\s+rep|sales\s+associate|payroll|"
    r"human\s+resources|hr\s+manager|marketing\s+manager|product\s+marketing|"
    r"customer\s+success|facilities|office\s+manager|bookkeeper|tax)\b",
    re.IGNORECASE,
)


def is_ai_sde_role(title: str, description: str = "") -> bool:
    """Determine if a job title matches genuine AI, Data, or Software Engineering roles."""
    t = (title or "").strip()
    if not t:
        return False
    if _NON_TECH_TITLE_RE.search(t) and not _CORE_ENG_RE.search(t):
        return False
    return bool(_AI_SDE_TITLE_RE.search(t))


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
    patterns = [
        ("greenhouse", r'(?:job-boards|boards)\.greenhouse\.io/([^/?#]+)'),
        ("greenhouse", r'greenhouse\.io/([^/?#]+)'),
        ("lever", r'lever\.co/([^/?#]+)'),
        ("ashby", r'ashbyhq\.com/([^/?#]+)'),
        ("workable", r'apply\.workable\.com/([^/?#]+)'),
        ("smartrecruiters", r'smartrecruiters\.com/([^/?#]+)'),
        ("bamboohr", r'([^./]+)\.bamboohr\.com'),
        ("freshteam", r'([^./]+)\.freshteam\.com'),
        ("zohorecruit", r'([^./]+)\.zohorecruit\.(?:in|com)'),
        ("keka", r'([^./]+)\.keka\.com'),
        ("param", r'([^./]+)\.param\.ai'),
        ("jobvite", r'jobs\.jobvite\.com/(?:careers/)?([^/?#]+)'),
        ("recruitee", r'([^./]+)\.recruitee\.com'),
        ("teamtailor", r'(?:career|jobs)?\.?([^./]+)\.teamtailor\.com'),
        ("breezy", r'([^./]+)\.breezy\.hr'),
        ("personio", r'([^./]+)\.jobs\.personio\.(?:de|com)'),
    ]
    for prov, pat in patterns:
        m = re.search(pat, url_str, re.IGNORECASE)
        if m:
            tok = m.group(1).strip()
            if tok.lower() not in ("embed", "jobs", "careers", "v1"):
                return prov, tok
    if "myworkdayjobs.com" in url_str.lower():
        parsed = urlparse(url_str)
        host = parsed.netloc.lower()
        tenant = host.split(".")[0]
        return "workday", f"{host}/{tenant}/External"
    return None, None


def _brand_tokens(company_name: str) -> list[str]:
    cleaned = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", company_name.lower())
    cleaned = re.sub(r"\b(pvt|ltd|limited|private|inc|llc|corp|technologies|solutions|ai|labs)\b", "", cleaned)
    return [t for t in re.findall(r"[a-z0-9]{3,}", cleaned)]


def verify_domain_with_http(domain: str, company_name: str, client: httpx.Client | None = None) -> bool:
    """Verify domain is live and page title/content matches company brand tokens."""
    if not domain or is_aggregator_or_ats_domain(domain):
        return False
    tokens = _brand_tokens(company_name)
    if not tokens:
        return False
    close_client = False
    if client is None:
        client = httpx.Client(follow_redirects=True, timeout=5.0)
        close_client = True
    try:
        for scheme in ("https", "http"):
            try:
                resp = client.get(f"{scheme}://{domain}", timeout=5.0)
                if resp.status_code < 400:
                    head = resp.text[:4000].lower()
                    title_m = re.search(r"<title[^>]*>(.*?)</title>", head, re.S)
                    title_txt = title_m.group(1) if title_m else ""
                    if any(tok in title_txt for tok in tokens) or any(tok in head[:1500] for tok in tokens):
                        return True
            except Exception:
                continue
        return False
    finally:
        if close_client:
            client.close()


def crawl_custom_careers_page(
    careers_url: str,
    company_name: str,
    client: httpx.Client | None = None,
) -> tuple[list[dict[str, Any]], list[str], str | None]:
    """Crawl a custom /careers page to extract JSON-LD jobs, direct job links, ATS embeds, and mailto emails."""
    if not careers_url or not careers_url.startswith(("http://", "https://")):
        return [], [], None
    close_client = False
    if client is None:
        client = httpx.Client(follow_redirects=True, timeout=6.0)
        close_client = True
    try:
        resp = client.get(careers_url, timeout=6.0)
        if resp.status_code >= 400:
            return [], [], None
        html_text = resp.text

        # 1. Check embedded ATS links or iframes
        detected_ats_url: str | None = None
        ats_urls = extract_ats_urls(html_text)
        if ats_urls:
            detected_ats_url = ats_urls[0]
        else:
            for m in re.finditer(r'<(?:iframe|a)[^>]+(?:src|href)=["\']([^"\']+)["\']', html_text, re.IGNORECASE):
                cand = m.group(1)
                if any(k in cand.lower() for k in ("greenhouse.io", "lever.co", "ashbyhq.com", "workable.com", "smartrecruiters.com", "zohorecruit.", "freshteam.com", "keka.com", "param.ai", "jobvite.com")):
                    detected_ats_url = cand
                    break

        # 2. Extract JSON-LD JobPostings
        jobs = extract_jsonld_jobpostings(html_text, base_url=careers_url)

        # 3. Extract direct job/Google Form anchor links when JSON-LD absent
        if not jobs:
            parsed_base = urlparse(careers_url)
            base_origin = f"{parsed_base.scheme}://{parsed_base.netloc}"
            seen_u: set[str] = set()
            for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html_text, re.I | re.S):
                href = m.group(1).strip()
                label = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2))).strip()
                if not href or href.startswith(("#", "javascript:", "mailto:")):
                    continue
                if href.startswith("/"):
                    href = base_origin + href
                if not href.startswith("http"):
                    continue
                low_h = href.lower()
                is_job_link = (
                    any(k in low_h for k in ("/jobs/", "/job/", "/careers/", "/opening", "/position", "docs.google.com/forms", "forms.gle"))
                    and low_h.rstrip("/") != careers_url.lower().rstrip("/")
                )
                if is_job_link and href not in seen_u and len(label) >= 4 and is_ai_sde_role(label):
                    seen_u.add(href)
                    jobs.append({
                        "title": label[:120],
                        "url": href,
                        "company": company_name,
                        "location": "India / Remote",
                        "description": f"Extracted from {careers_url}",
                    })

        # 4. Extract mailto / public emails
        emails: list[str] = []
        seen_e: set[str] = set()
        for em in re.findall(r"(?:mailto:)?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", html_text):
            em_low = em.lower().rstrip(".")
            dom = em_low.split("@", 1)[1]
            if em_low not in seen_e and not is_aggregator_or_ats_domain(dom) and not any(x in em_low for x in ("example.com", "sentry.io", "wixpress.com", ".png", ".jpg")):
                seen_e.add(em_low)
                emails.append(em_low)

        return jobs, emails, detected_ats_url
    except Exception as e:
        logger.debug("Custom career crawl notice for %s (%s): %s", company_name, careers_url, e)
        return [], [], None
    finally:
        if close_client:
            client.close()


def process_single_company(
    company: dict[str, Any],
    client: httpx.Client | None = None,
    conn: sqlite3.Connection | None = None,
    resolve_missing: bool = False,
) -> dict[str, Any]:
    """Execute complete deep loop on a single company."""
    if conn is None:
        conn = get_connection()
    c_name = (company.get("company_name") or "").strip()

    if company.get("stage") == "gtm_excluded" or c_name.lower() == "revcloud":
        return {
            "company": c_name,
            "domain": company.get("official_domain"),
            "skipped": "gtm_excluded",
            "mx_valid": False,
            "mx_provider": "none",
            "ats_provider": company.get("ats_provider"),
            "ats_token": company.get("ats_board_token"),
            "emails_added": 0,
            "total_emails": 0,
            "total_jobs_polled": 0,
            "ai_sde_roles_found": 0,
            "new_jobs_stored": 0,
        }

    c_domain = _clean_domain_token(company.get("official_domain")) or ""
    if c_domain and is_aggregator_or_ats_domain(c_domain):
        c_domain = ""
    careers_url = company.get("careers_page_url") or ""
    ats_prov = company.get("ats_provider")
    ats_token = company.get("ats_board_token")

    # 1. Resolve verified non-aggregator domain (NO blind {slug}.com guessing)
    c_name_lower = c_name.lower().strip()
    if c_name_lower in DOMAIN_OVERRIDES:
        c_domain = DOMAIN_OVERRIDES[c_name_lower]
    elif not c_domain:
        if careers_url and "://" in careers_url:
            cand = _clean_domain_token(careers_url)
            if cand and "." in cand and not is_aggregator_or_ats_domain(cand):
                c_domain = cand
        if not c_domain and resolve_missing:
            try:
                resolved_url = resolve_company_career_page(c_name)
                if resolved_url:
                    cand = _clean_domain_token(resolved_url)
                    if cand and "." in cand and not is_aggregator_or_ats_domain(cand) and not any(s in cand for s in ("google.", "bing.", "duckduckgo.", "wikipedia.org", "crunchbase.com", "pitchbook.com", "tracxn.com", "zaubacorp.com", "tofler.in")):
                        if verify_domain_with_http(cand, c_name, client=client):
                            c_domain = cand
                            if not careers_url:
                                careers_url = resolved_url
            except Exception as e:
                logger.debug("Domain resolution notice for %s: %s", c_name, e)

    # 2. Check MX Deliverability only on verified non-aggregator domain
    mx_valid, mx_provider = get_cached_mx(c_domain) if (c_domain and not is_aggregator_or_ats_domain(c_domain)) else (False, "none")

    # 3. Harvest Corporate & Decision-Maker Inboxes
    existing_leads = conn.execute(
        "SELECT contact_email FROM recruiter_leads WHERE LOWER(company_name) = ? AND contact_email NOT LIKE '%@connect.linkedin.com'",
        (c_name.lower(),),
    ).fetchall()
    existing_emails = {r[0].lower().strip() for r in existing_leads if r[0]}
    emails_added = 0

    if mx_valid and c_domain and len(existing_emails) < 5:
        standard_prefixes = [
            ("careers", "Head of Talent / Recruiting", "recruiter", 0.95),
            ("talent", "Talent Acquisition Lead", "recruiter", 0.94),
            ("hiring", "Technical Hiring Manager", "hiring_manager", 0.92),
            ("engineering", "VP of Engineering / Tech Lead", "hiring_manager", 0.88),
            ("founders", "Founding Team", "founder", 0.85),
        ]
        for prefix, role, c_type, _conf in standard_prefixes:
            em = f"{prefix}@{c_domain}".lower()
            if em not in existing_emails:
                existing_emails.add(em)
                try:
                    store_recruiter_lead(
                        contact_email=em,
                        role_title=f"{role} at {c_name}",
                        company_name=c_name,
                        company_domain=c_domain,
                        contact_name=f"{c_name} {role}",
                        contact_type=c_type,
                        source_platform=f"mx_verified_{mx_provider}",
                        evidence_snippet=f"Verified corporate mail exchanger ({mx_provider}) with active MX route",
                        execution_route="DUAL_ATTACK",
                        outreach_status="queued",
                        persona="Engineering Leadership" if "Engineering" in role else "Talent & Recruiting",
                        conn=conn,
                    )
                    emails_added += 1
                except Exception as e:
                    logger.warning("Failed storing MX lead %s for %s: %s", em, c_name, e)

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

    # 5. Poll Open Jobs (ATS or Custom /careers HTML Crawl)
    discovered_jobs: list[dict[str, Any]] = []
    if ats_prov and ats_token:
        try:
            discovered_jobs = poll_board(ats_prov, ats_token, client=client)
        except Exception as e:
            logger.debug("ATS poll notice for %s (%s/%s): %s", c_name, ats_prov, ats_token, e)
    elif careers_url and "://" in careers_url:
        c_jobs, c_emails, embedded_ats_url = crawl_custom_careers_page(careers_url, c_name, client=client)
        if embedded_ats_url:
            e_prov, e_tok = resolve_ats_from_url(embedded_ats_url)
            if e_prov and e_tok:
                ats_prov, ats_token = e_prov, e_tok
                try:
                    discovered_jobs = poll_board(ats_prov, ats_token, client=client)
                except Exception:
                    pass
        if not discovered_jobs:
            discovered_jobs = c_jobs
        for em in c_emails:
            if em not in existing_emails:
                existing_emails.add(em)
                try:
                    store_recruiter_lead(
                        contact_email=em,
                        role_title=f"Careers Page Contact at {c_name}",
                        company_name=c_name,
                        company_domain=c_domain or em.split("@", 1)[1],
                        contact_name=f"{c_name} Hiring Team",
                        contact_type="recruiter",
                        source_platform="careers_page_scrape",
                        evidence_snippet=f"Extracted directly from {careers_url}",
                        execution_route="DUAL_ATTACK",
                        outreach_status="queued",
                        persona="Talent & Recruiting",
                        conn=conn,
                    )
                    emails_added += 1
                except Exception as e:
                    logger.warning("Failed storing scraped email %s for %s: %s", em, c_name, e)

    # Filter for AI and SDE roles and deduplicate by (LOWER(company), normalized_title) & URL
    ai_sde_jobs = [j for j in discovered_jobs if is_ai_sde_role(j.get("title", ""), j.get("description", ""))]
    new_jobs_stored = 0

    existing_ct = {
        (r[0].strip().lower(), re.sub(r"\s+", " ", r[1].strip().lower()))
        for r in conn.execute(
            "SELECT company, title FROM jobs WHERE LOWER(company) = ? AND title IS NOT NULL",
            (c_name.lower(),),
        ).fetchall()
    }

    has_email = len(existing_emails) > 0
    route = "DUAL_ATTACK" if has_email else "PORTAL_ONLY"

    for j in ai_sde_jobs:
        j_url = j.get("url")
        j_title = j.get("title")
        if not j_url or not j_title:
            continue
        ct_key = (c_name.lower(), re.sub(r"\s+", " ", j_title.strip().lower()))
        if ct_key in existing_ct:
            continue
        existing_ct.add(ct_key)
        try:
            canon_url = canonicalize_application_url(j_url)
            new_cnt, _ = store_jobs(
                conn=conn,
                jobs=[{
                    "url": j_url,
                    "title": j_title,
                    "company": c_name,
                    "location": j.get("location", "Remote / Hybrid"),
                    "description": j.get("description", "")[:1000],
                }],
                site=ats_prov or "company_looper",
                strategy="all_companies_looper",
            )
            if new_cnt > 0:
                conn.execute(
                    "UPDATE jobs SET company = COALESCE(company, ?), execution_route = ? WHERE url = ?",
                    (c_name, route, canon_url),
                )
                commit_with_retry(conn)
                new_jobs_stored += 1
        except Exception as e:
            logger.warning("Failed storing job %s for %s: %s", j_url, c_name, e)

    # 6. Update Watchlist Entry (safely respecting unique domain index)
    now_iso = datetime.now(timezone.utc).isoformat()
    total_roles = len(discovered_jobs) if discovered_jobs else company.get("open_roles_count", 0)
    safe_domain = c_domain or None
    if safe_domain:
        conflict = conn.execute(
            "SELECT company_id FROM career_watchlist WHERE LOWER(official_domain) = ? AND company_id != ? LIMIT 1",
            (safe_domain.lower(), company["company_id"]),
        ).fetchone()
        if conflict:
            safe_domain = None

    conn.execute(
        """
        UPDATE career_watchlist
        SET official_domain = COALESCE(official_domain, ?),
            careers_page_url = COALESCE(careers_page_url, ?),
            ats_provider = COALESCE(ats_provider, ?),
            ats_board_token = COALESCE(ats_board_token, ?),
            open_roles_count = ?,
            last_checked_at = ?
        WHERE company_id = ?
        """,
        (safe_domain, careers_url or None, ats_prov, ats_token, total_roles, now_iso, company["company_id"]),
    )
    commit_with_retry(conn)

    return {
        "company": c_name,
        "domain": safe_domain or company.get("official_domain"),
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
    parser.add_argument("--resolve-missing", action="store_true", help="Resolve missing official domains via DDG + HTTP title check.")
    parser.add_argument("--research-only", action="store_true", help="Only process newly ingested/merged research companies (metadata_json IS NOT NULL).")
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
            stage,
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

    if args.research_only:
        query += " AND metadata_json IS NOT NULL"

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
                executor.submit(process_single_company, comp, client, None, args.resolve_missing): comp for comp in filtered
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
                        DATA_DIR.mkdir(parents=True, exist_ok=True)
                        cp_path = DATA_DIR / "all_companies_looper_progress.json"
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
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    final_report_path = DATA_DIR / "all_companies_looper_final_report.json"
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
