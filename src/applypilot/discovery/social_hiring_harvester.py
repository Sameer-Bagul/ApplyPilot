"""Social Hiring Harvester for LinkedIn & X Public Posts.

Mines public hiring announcements on LinkedIn (site:linkedin.com/posts) and X (site:x.com)
to discover:
1. Active hiring posts and quotes from founders, CTOs, and recruiters.
2. Direct contact emails explicitly shared in post text.
3. High-signal conversation hooks for cold outreach emails.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from typing import Any

from applypilot.discovery.lead_extractor import extract_emails

logger = logging.getLogger(__name__)

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

AUTHOR_TITLE_PATTERNS = [
    re.compile(r"^([^:|–—]+)\s*(?:on LinkedIn|on X|/\s*X):\s*[\"']?(.*)$", re.IGNORECASE),
    re.compile(r"^([^:|–—]+)\s*[-–—]\s*(?:Posts|Post|Status)", re.IGNORECASE),
]


def parse_social_post_hit(hit: dict[str, str], company_name: str, platform: str) -> dict[str, Any] | None:
    """Parse a search engine hit representing a social post into structured hiring intel."""
    href = (hit.get("url") or hit.get("href") or "").strip()
    title = (hit.get("title") or "").strip()
    body = (hit.get("body") or hit.get("snippet") or "").strip()

    if not href:
        return None

    full_text = f"{title} {body}"

    # Extract author name
    author_name = ""
    for pat in AUTHOR_TITLE_PATTERNS:
        m = pat.search(title)
        if m:
            author_name = m.group(1).strip()
            break

    if not author_name:
        # Fallback: check first 2 words if capitalized
        words = title.split()
        if len(words) >= 2 and words[0][0].isupper() and words[1][0].isupper():
            if company_name.lower() not in f"{words[0]} {words[1]}".lower():
                author_name = f"{words[0]} {words[1]}"

    if author_name:
        author_name = re.sub(r"[,;:\'\"\(\)\[\]]+$", "", author_name).strip()

    # Extract emails explicitly stated in the post text
    embedded_emails = extract_emails(full_text)

    # Clean quote snippet
    quote_snippet = body[:280] if body else title[:280]

    return {
        "platform": platform,
        "author_name": author_name or f"{company_name} Hiring Lead",
        "post_url": href,
        "post_title": title,
        "post_quote": quote_snippet,
        "embedded_emails": embedded_emails,
        "evidence_snippet": f"Found on {platform.replace('_', ' ').title()}: \"{quote_snippet}\"",
    }


class SocialHiringHarvester:
    """Harvests public hiring posts from LinkedIn and X without login."""

    def __init__(self, conn: sqlite3.Connection | None = None, max_results: int = 5):
        self.conn = conn
        self.max_results = max_results

    def harvest_company_hiring_posts(
        self,
        company_name: str,
        domain: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search public LinkedIn and X posts for hiring signals and direct emails."""
        c_name = (company_name or "").strip()
        if not c_name:
            return []

        posts: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        queries = [
            (f'"{c_name}" ("we are hiring" OR "we\'re hiring" OR "looking for an engineer" OR "email me at" OR "dm me") site:linkedin.com/posts', "linkedin_post"),
            (f'"{c_name}" ("we are hiring" OR "hiring engineers" OR "looking for a founding" OR "send resume") site:x.com', "x_post"),
        ]

        if DDGS is None:
            return []

        try:
            with DDGS(timeout=4) as ddgs:
                for q, platform in queries:
                    try:
                        hits = list(ddgs.text(q, max_results=self.max_results))
                        for h in hits:
                            u = h.get("href") or h.get("url") or ""
                            if not u or u in seen_urls:
                                continue
                            seen_urls.add(u)

                            parsed = parse_social_post_hit(h, c_name, platform)
                            if parsed:
                                posts.append(parsed)
                    except Exception as e:
                        logger.debug("Social hiring search notice for '%s': %s", q, e)
                        break
        except Exception as e:
            logger.debug("DDGS client unavailable for social hiring: %s", e)

        return posts

    def persist_posts_to_leads(
        self,
        posts: list[dict[str, Any]],
        company_name: str,
        domain: str | None = None,
        conn: sqlite3.Connection | None = None,
    ) -> int:
        """Persist discovered social hiring contacts into recruiter_leads."""
        active_conn = conn or self.conn
        if not active_conn or not posts:
            return 0

        from applypilot.database import store_recruiter_lead
        added = 0
        clean_d = (domain or "").lower().replace("www.", "").strip()

        for p in posts:
            author = p.get("author_name") or f"{company_name} Lead"
            emails = p.get("embedded_emails") or []
            post_url = p.get("post_url") or ""
            evidence = p.get("evidence_snippet") or ""

            # Use embedded email or synthetic alias
            clean_author_handle = re.sub(r"[^a-zA-Z0-9\s]", "", author).strip().lower().replace(" ", ".")
            synth_domain = clean_d or f"{re.sub(r'[^a-zA-Z0-9]', '', company_name).lower()}.com"
            dest_email = emails[0] if emails else f"{clean_author_handle}@{synth_domain}"

            try:
                store_recruiter_lead(
                    contact_email=dest_email,
                    role_title=f"Hiring Lead at {company_name}",
                    company_name=company_name,
                    company_domain=clean_d,
                    contact_name=author,
                    contact_type="hiring_manager",
                    persona="hiring_manager",
                    source_platform=p.get("platform", "social_post"),
                    source_post_url=post_url,
                    evidence_snippet=evidence,
                    execution_route="DUAL_ATTACK",
                    conn=active_conn,
                )
                added += 1
            except Exception as e:
                logger.debug("Failed saving social hiring lead: %s", e)

        return added
