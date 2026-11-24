"""Deep Web Searcher for Organic Google & DDG Pages 1 & 2.

Explores organic external search results (articles, blogs, press releases, interviews)
to harvest:
1. Executive quotes and leadership mentions (Founders, CTOs, Tech Leads)
2. Public corporate and personal email addresses
3. Recent milestones and funding news for high-conversion outreach context
"""

from __future__ import annotations

import logging
import re
from typing import Any
import urllib.parse

import httpx

from applypilot.discovery.lead_extractor import extract_emails

logger = logging.getLogger(__name__)

SKIP_DOMAINS = {
    "facebook.com", "instagram.com", "twitter.com", "x.com", "youtube.com",
    "tiktok.com", "pinterest.com", "reddit.com", "quora.com", "wikipedia.org",
    "glassdoor.com", "indeed.com", "linkedin.com/in", "linkedin.com/jobs",
}

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

QUOTE_PATTERNS = [
    re.compile(r'([A-Z][a-z]+ [A-Z][a-z]+),\s*(?:co-founder|founder|ceo|cto|head of engineering|vp of engineering)(?:(?:\s+and\s+|\s*/\s*|\s*,\s*)(?:co-founder|founder|ceo|cto))?\s*(?:of|at)\s*([^,.\n]+)', re.IGNORECASE),
    re.compile(r'(?:said|stated|explained|noted)\s*([A-Z][a-z]+ [A-Z][a-z]+),\s*(?:co-founder|founder|ceo|cto)', re.IGNORECASE),
    re.compile(r'([A-Z][a-z]+ [A-Z][a-z]+)\s*(?:is|was)\s*(?:the\s+)?(?:co-founder|founder|ceo|cto)', re.IGNORECASE),
    re.compile(r'according to\s*([A-Z][a-z]+ [A-Z][a-z]+),\s*(?:co-founder|founder|ceo|cto)', re.IGNORECASE),
]


def is_valid_article_url(url: str) -> bool:
    """Filter out social networks, aggregators, and non-article endpoints."""
    if not url or not url.startswith(("http://", "https://")):
        return False
    u_lower = url.lower()
    if any(skip in u_lower for skip in SKIP_DOMAINS):
        return False
    if any(ext in u_lower for ext in [".pdf", ".png", ".jpg", ".jpeg", ".mp4", ".zip"]):
        return False
    return True


class DeepWebSearcher:
    """Searches and parses organic search hits on Page 1 and Page 2."""

    def __init__(self, timeout: float = 3.5, max_pages: int = 5):
        self.timeout = timeout
        self.max_pages = max_pages

    def search_and_analyze_company(
        self,
        company_name: str,
        domain: str | None = None,
    ) -> dict[str, Any]:
        """Perform deep multi-site search across Pages 1 and 2 for articles and quotes."""
        c_name = (company_name or "").strip()
        c_domain = (domain or "").lower().replace("www.", "").strip()
        if not c_name:
            return {"articles_checked": 0, "discovered_emails": [], "discovered_leaders": [], "company_milestones": []}

        search_hits = self._fetch_search_hits(c_name)
        valid_urls = [h["url"] for h in search_hits if is_valid_article_url(h["url"])][:self.max_pages]

        discovered_emails: set[str] = set()
        discovered_leaders: list[dict[str, Any]] = []
        milestones: list[str] = []
        seen_names: set[str] = set()

        for url in valid_urls:
            try:
                page_data = self._fetch_and_parse_article(url, c_name, c_domain)
                for em in page_data.get("emails", []):
                    discovered_emails.add(em)
                for ldr in page_data.get("leaders", []):
                    name = ldr.get("name")
                    if name and name not in seen_names:
                        seen_names.add(name)
                        discovered_leaders.append(ldr)
                for m in page_data.get("milestones", []):
                    if m not in milestones:
                        milestones.append(m)
            except Exception as e:
                logger.debug("Failed parsing organic article %s: %s", url, e)

        return {
            "articles_checked": len(valid_urls),
            "discovered_emails": sorted(list(discovered_emails)),
            "discovered_leaders": discovered_leaders,
            "company_milestones": milestones[:5],
        }

    def _fetch_search_hits(self, company_name: str) -> list[dict[str, str]]:
        """Query DDGS for organic editorial and news hits."""
        hits: list[dict[str, str]] = []
        queries = [
            f'"{company_name}" (startup OR "funding" OR "engineering" OR "interview" OR "podcast")',
            f'"{company_name}" ("CTO" OR "Founder" OR "Head of Engineering" OR "CEO")',
        ]

        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS

            with DDGS(timeout=4) as ddgs:
                for q in queries:
                    try:
                        res = list(ddgs.text(q, max_results=6))
                        for r in res:
                            href = r.get("href") or ""
                            title = r.get("title") or ""
                            body = r.get("body") or ""
                            if href:
                                hits.append({"url": href, "title": title, "body": body})
                    except Exception as e:
                        logger.debug("DDGS organic query notice for '%s': %s", q, e)
                        break
        except Exception as e:
            logger.debug("DDGS client unavailable: %s", e)

        return hits

    def _fetch_and_parse_article(
        self,
        url: str,
        company_name: str,
        company_domain: str,
    ) -> dict[str, Any]:
        """Fetch article HTML, extract emails, leadership quotes, and milestone text."""
        result: dict[str, Any] = {"emails": [], "leaders": [], "milestones": []}

        with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=DEFAULT_HEADERS) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return result

            html_text = resp.text
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_text, "html.parser")

            # Remove scripts, styles, navigations
            for s in soup(["script", "style", "nav", "footer", "header"]):
                s.decompose()

            body_text = soup.get_text(separator=" ", strip=True)

            # 1. Extract emails
            scraped_emails = extract_emails(body_text)
            for em in scraped_emails:
                if company_domain and company_domain in em:
                    result["emails"].append(em)
                elif em.endswith("@gmail.com"):
                    result["emails"].append(em)

            # 2. Extract quotes & leadership mentions
            for p_tag in soup.find_all(["p", "blockquote", "h2", "h3"]):
                text = p_tag.get_text(separator=" ", strip=True)
                if not text or len(text) < 20:
                    continue

                for pat in QUOTE_PATTERNS:
                    match = pat.search(text)
                    if match:
                        name = match.group(1).strip()
                        # Avoid company name false matches
                        if company_name.lower() not in name.lower() and len(name.split()) == 2:
                            result["leaders"].append({
                                "name": name,
                                "role": "Executive / Leadership",
                                "quote": text[:200],
                                "source_url": url,
                            })
                            break

                # 3. Detect funding or expansion milestones
                if any(k in text.lower() for k in ["raised $", "series a", "series b", "seed funding", "hiring aggressively", "launched our new"]):
                    if len(text) < 250:
                        result["milestones"].append(text)

        return result
