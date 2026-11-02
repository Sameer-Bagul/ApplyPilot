"""Career Site Resolver: Resolves company names and social posts to official ATS portals.

When a post mentions that a company is hiring without a direct ATS link:
1. Searches DuckDuckGo for the company's official /careers page.
2. Inspects outbound links to locate underlying Greenhouse, Lever, Ashby, or Workday forms.
3. Unshortens redirected tracking links (e.g. bit.ly, t.co, lnkd.in).
"""

from __future__ import annotations

import logging
import re
import urllib.parse
import urllib.request
from typing import Any
from urllib.parse import urlparse

from applypilot.social_discovery.dork_searcher import search_duckduckgo_html
from applypilot.social_discovery.extractor import KNOWN_ATS_DOMAINS, extract_ats_urls

logger = logging.getLogger(__name__)

_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

# Shortener domains to resolve
SHORTENER_DOMAINS = {
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "lnkd.in",
    "linktr.ee",
    "goo.gl",
    "ow.ly",
    "buff.ly",
}


def unshorten_url(url: str, timeout: float = 6.0) -> str:
    """Follow HTTP redirects to unshorten shortened links."""
    parsed = urlparse(url)
    if parsed.netloc.lower() not in SHORTENER_DOMAINS:
        return url

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": _USER_AGENT},
            method="HEAD",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.geturl()
    except Exception:
        # Fallback with GET if HEAD not supported
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.geturl()
        except Exception:
            return url


def resolve_company_career_page(company_name: str, timeout: float = 8.0) -> str | None:
    """Find official careers/jobs page for a company via search engine."""
    clean_name = company_name.strip().strip("\"'")
    if not clean_name:
        return None

    query = f'"{clean_name}" official site careers OR jobs'
    hits = search_duckduckgo_html(query, max_results=5, timeout=timeout)

    for hit in hits:
        hit_url = hit.get("url", "")
        parsed = urlparse(hit_url)
        path = parsed.path.lower()
        domain = parsed.netloc.lower()

        # Check if direct ATS link
        if any(ats in domain for ats in KNOWN_ATS_DOMAINS):
            return hit_url

        # Check for career page indicators in path
        if any(term in path for term in ("career", "jobs", "join", "work-with-us", "positions", "openings")):
            return hit_url

    return hits[0]["url"] if hits else None


def extract_ats_from_page(page_url: str, timeout: float = 8.0) -> str | None:
    """Fetch careers page HTML and extract direct ATS application links."""
    req = urllib.request.Request(
        page_url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html_text = resp.read().decode("utf-8", errors="replace")

        # Check for embedded ATS links in HTML
        ats_urls = extract_ats_urls(html_text)
        if ats_urls:
            return ats_urls[0]

        # Check for iframe src pointing to ATS
        iframe_matches = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
        for src in iframe_matches:
            if any(ats in src.lower() for ats in KNOWN_ATS_DOMAINS):
                return src

    except Exception as e:
        logger.warning("Error fetching careers page '%s': %s", page_url, e)

    return None


def resolve_company_ats(company_name: str) -> dict[str, Any]:
    """End-to-end resolution of company name -> careers page -> direct ATS portal link."""
    career_url = resolve_company_career_page(company_name)
    resolved_ats_url = None
    ats_type = "unknown"

    if career_url:
        parsed = urlparse(career_url)
        domain = parsed.netloc.lower()
        if any(ats in domain for ats in KNOWN_ATS_DOMAINS):
            resolved_ats_url = career_url
        else:
            resolved_ats_url = extract_ats_from_page(career_url)

    if resolved_ats_url:
        for ats in ("greenhouse", "lever", "ashby", "workday", "smartrecruiters", "bamboohr"):
            if ats in resolved_ats_url.lower():
                ats_type = ats
                break

    return {
        "company_name": company_name,
        "careers_page_url": career_url,
        "resolved_ats_url": resolved_ats_url,
        "ats_type": ats_type,
    }
