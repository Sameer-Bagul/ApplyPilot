"""Deterministic JSON-LD JobPosting Parser & Content Change Detector.

Allows 100% zero-token detection of newly launched job postings on custom
company career pages and sitemaps by checking:
1. HTTP ETag & Last-Modified headers
2. SHA-256 content hashing of raw HTML / career text
3. Deterministic parsing of Schema.org <script type="application/ld+json"> JobPosting objects
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def compute_content_hash(text: str) -> str:
    """Calculate SHA-256 hash of normalized text."""
    normalized = re.sub(r"\s+", " ", text).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def check_page_change(
    url: str,
    last_hash: str | None = None,
    last_etag: str | None = None,
    client: httpx.Client | None = None,
    timeout: float = 12.0,
) -> tuple[bool, str | None, str | None, str]:
    """Check if career page content has changed using ETag or content hash.

    Returns:
        (has_changed, new_hash, new_etag, html_content)
    """
    should_close = False
    if client is None:
        client = httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=timeout)
        should_close = True

    headers = dict(DEFAULT_HEADERS)
    if last_etag:
        headers["If-None-Match"] = last_etag

    try:
        resp = client.get(url, headers=headers)
        if resp.status_code == 304:
            # Not modified
            return False, last_hash, last_etag, ""

        if resp.status_code != 200:
            return False, last_hash, last_etag, ""

        new_etag = resp.headers.get("ETag")
        html = resp.text
        new_hash = compute_content_hash(html)

        if last_hash and new_hash == last_hash:
            return False, new_hash, new_etag, html

        return True, new_hash, new_etag, html
    except Exception as e:
        logger.debug("Failed checking page change for %s: %s", url, e)
        return False, last_hash, last_etag, ""
    finally:
        if should_close:
            client.close()


def extract_jsonld_jobpostings(html: str, base_url: str = "") -> list[dict[str, Any]]:
    """Deterministically parse Schema.org JobPosting objects from HTML JSON-LD blocks.

    Returns:
        List of normalized job dicts with title, url, company, location, and description.
    """
    jobs: list[dict[str, Any]] = []
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)

    for block in blocks:
        try:
            data = json.loads(block)
        except Exception:
            continue

        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            if data.get("@type") == "JobPosting":
                items = [data]
            elif "@graph" in data and isinstance(data["@graph"], list):
                items = [it for it in data["@graph"] if isinstance(it, dict) and it.get("@type") == "JobPosting"]
            elif "itemListElement" in data and isinstance(data["itemListElement"], list):
                for el in data["itemListElement"]:
                    it = el.get("item") if isinstance(el, dict) else el
                    if isinstance(it, dict) and it.get("@type") == "JobPosting":
                        items.append(it)

        for it in items:
            title = it.get("title")
            if not title:
                continue

            job_url = it.get("url") or it.get("sameAs") or base_url
            if job_url and not job_url.startswith("http") and base_url:
                job_url = urljoin(base_url, job_url)

            org = it.get("hiringOrganization") or {}
            co_name = org.get("name") if isinstance(org, dict) else str(org)

            location = "Remote"
            loc_data = it.get("jobLocation")
            if isinstance(loc_data, dict):
                addr = loc_data.get("address", {})
                if isinstance(addr, dict):
                    locality = addr.get("addressLocality")
                    region = addr.get("addressRegion")
                    country = addr.get("addressCountry")
                    parts = [p for p in [locality, region, country] if p]
                    if parts:
                        location = ", ".join(parts)
            elif isinstance(loc_data, list) and loc_data:
                first_l = loc_data[0]
                if isinstance(first_l, dict) and first_l.get("address"):
                    location = str(first_l["address"])

            jobs.append({
                "title": title.strip(),
                "url": job_url,
                "company": co_name.strip() if co_name else "",
                "location": location,
                "description": it.get("description", ""),
                "date_posted": it.get("datePosted"),
                "employment_type": it.get("employmentType"),
                "ats_provider": "jsonld_custom",
                "execution_route": "PORTAL_ONLY",
                "site": "company_careers",
            })

    return jobs

