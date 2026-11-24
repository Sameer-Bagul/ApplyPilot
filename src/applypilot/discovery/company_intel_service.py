"""Company Intelligence Service with Unified 30-Day Research Caching.

Aggregates:
1. Local Database (existing open jobs & fit scores)
2. Wikipedia & Wikidata REST API (company background, founders, products)
3. GitHub Org API (active repositories, tech stack & languages)
4. Public ATS feeds & Watchlist data

Avoids repeated research per company by storing results in the `company_intel` table.
All leads sharing the same company or domain leverage the cached intelligence.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any
import sqlite3

from applypilot.database import (
    get_company_intel,
    get_connection,
    save_company_intel,
)
from applypilot.discovery.company_osint import (
    investigate_company_github_projects,
    investigate_company_wikipedia,
)

logger = logging.getLogger("applypilot.company_intel")

AI_KEYWORDS = {
    "ai", "llm", "agent", "agentic", "rag", "machine learning", "deep learning",
    "neural", "gpt", "nlp", "computer vision", "generative ai", "langchain",
    "langgraph", "vector", "embedding", "vllm", "ollama", "transformers"
}


def _detect_ai_focus(text: str, tech_stack: list[str]) -> list[str]:
    """Detect AI & advanced technology focus tags from summary and stack."""
    found: set[str] = set()
    lower = text.lower()
    for kw in AI_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", lower):
            found.add(kw.title())
    for t in tech_stack:
        if t.lower() in AI_KEYWORDS:
            found.add(t.title())
    return sorted(list(found))


class CompanyIntelService:
    """Manages company background investigation with intelligent multi-source aggregation and caching."""

    def __init__(self, conn: sqlite3.Connection | None = None) -> None:
        self.conn = conn

    def get_or_research(
        self,
        company_name: str,
        domain: str | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Retrieve cached company intel or perform fresh multi-source research."""
        c_name = (company_name or "").strip()
        c_domain = (domain or "").strip().lower()

        # Key for lookup: prefer domain if available, else clean company name
        cache_key = c_domain or c_name.lower()
        if not cache_key:
            return {
                "company_name": "Unknown",
                "official_domain": "",
                "tech_stack": [],
                "open_roles": [],
                "wikipedia_summary": "",
                "ai_focus_tags": [],
            }

        # 1. Check SQLite 30-day cache
        if not force_refresh:
            cached = get_company_intel(cache_key, conn=self.conn)
            if not cached and c_name:
                cached = get_company_intel(c_name.lower(), conn=self.conn)

            if cached:
                logger.debug("Reusing cached intel for company %s (key=%s)", c_name, cache_key)
                return self._format_intel_dict(cached)

        # 2. Cache miss -> Perform fresh investigation
        logger.info("Performing fresh company research for '%s' (domain=%s)", c_name, c_domain)
        conn = self.conn or get_connection()

        # (a) Check local database for existing open jobs
        local_jobs: list[dict[str, Any]] = []
        try:
            query = """
                SELECT title, url, fit_score, location, salary 
                FROM jobs 
                WHERE (LOWER(company) = LOWER(?) OR (? != '' AND LOWER(url) LIKE ?))
                ORDER BY fit_score DESC LIMIT 5
            """
            domain_like = f"%{c_domain}%" if c_domain else ""
            rows = conn.execute(query, (c_name, c_domain, domain_like)).fetchall()
            local_jobs = [
                {
                    "title": r[0],
                    "url": r[1],
                    "fit_score": r[2] or 0,
                    "location": r[3] or "",
                    "salary": r[4] or "",
                }
                for r in rows
            ]
        except Exception as e:
            logger.debug("Local jobs lookup error for %s: %s", c_name, e)

        # (b) Query Wikipedia REST API
        wiki_summary = ""
        wiki_founders: list[str] = []
        try:
            wiki_res = investigate_company_wikipedia(c_name)
            if wiki_res.get("found"):
                wiki_summary = wiki_res.get("summary", "")
        except Exception as e:
            logger.debug("Wikipedia query failed for %s: %s", c_name, e)

        # (c) Query GitHub Org API for public repositories and tech stack
        tech_stack: set[str] = set()
        gh_org = ""
        try:
            slug = c_domain.split(".")[0] if c_domain else c_name.replace(" ", "")
            gh_repos = investigate_company_github_projects(slug)
            if gh_repos:
                gh_org = f"https://github.com/{slug}"
                for r in gh_repos:
                    lang = r.get("language")
                    if lang:
                        tech_stack.add(lang)
                    desc = (r.get("description") or "").lower()
                    for tech in ["react", "fastapi", "docker", "kubernetes", "postgres", "redis", "pytorch", "next.js", "three.js", "playwright"]:
                        if tech in desc:
                            tech_stack.add(tech.title())
        except Exception as e:
            logger.debug("GitHub org query failed for %s: %s", c_name, e)

        # (d) Check career_watchlist for existing enrichment data
        funding_stage = ""
        try:
            w_row = conn.execute(
                """
                SELECT stage, total_funding, sector, tech_radar_json, open_roles_count 
                FROM career_watchlist 
                WHERE LOWER(company_name) = LOWER(?) OR (? != '' AND LOWER(official_domain) = LOWER(?))
                LIMIT 1
                """,
                (c_name, c_domain, c_domain),
            ).fetchone()
            if w_row:
                funding_stage = w_row[0] or w_row[1] or ""
                radar_raw = w_row[3]
                if radar_raw:
                    try:
                        radar_items = json.loads(radar_raw)
                        if isinstance(radar_items, list):
                            tech_stack.update(radar_items)
                    except Exception:
                        pass
        except Exception as e:
            logger.debug("Watchlist check notice for %s: %s", c_name, e)

        # (e) Detect AI focus tags
        combined_text = f"{c_name} {wiki_summary} {' '.join(tech_stack)} {' '.join(j['title'] for j in local_jobs)}"
        ai_tags = _detect_ai_focus(combined_text, list(tech_stack))

        # (f) Persist to company_intel
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=30)
        intel_record = {
            "domain_or_name": cache_key,
            "company_name": c_name or cache_key,
            "official_domain": c_domain,
            "wikipedia_summary": wiki_summary[:1000],
            "github_org": gh_org,
            "tech_stack_json": sorted(list(tech_stack)),
            "open_roles_json": local_jobs,
            "funding_stage": funding_stage,
            "ai_focus_tags": ai_tags,
            "researched_at": now.isoformat(),
            "expires_at": expires.isoformat(),
        }

        try:
            save_company_intel(intel_record, conn=conn)
        except Exception as e:
            logger.warning("Failed saving company_intel for %s: %s", cache_key, e)

        return self._format_intel_dict(intel_record)

    def enrich_batch_for_leads(self, leads: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """Research all unique companies in a list of leads, deduplicating lookups."""
        unique_companies: dict[str, tuple[str, str | None]] = {}
        for lead in leads:
            c_name = lead.get("company_name") or ""
            domain = lead.get("company_domain") or ""
            key = (domain or c_name).strip().lower()
            if key and key not in unique_companies:
                unique_companies[key] = (c_name, domain)

        company_map: dict[str, dict[str, Any]] = {}
        for key, (c_name, domain) in unique_companies.items():
            intel = self.get_or_research(c_name, domain=domain)
            company_map[key] = intel
            if c_name.lower() not in company_map:
                company_map[c_name.lower()] = intel
            if domain and domain.lower() not in company_map:
                company_map[domain.lower()] = intel

        return company_map

    @staticmethod
    def _format_intel_dict(row: dict[str, Any]) -> dict[str, Any]:
        """Parse JSON fields into native Python lists for downstream consumption."""
        tech_stack = row.get("tech_stack_json")
        if isinstance(tech_stack, str):
            try:
                tech_stack = json.loads(tech_stack)
            except Exception:
                tech_stack = []
        elif not isinstance(tech_stack, list):
            tech_stack = []

        open_roles = row.get("open_roles_json")
        if isinstance(open_roles, str):
            try:
                open_roles = json.loads(open_roles)
            except Exception:
                open_roles = []
        elif not isinstance(open_roles, list):
            open_roles = []

        ai_tags = row.get("ai_focus_tags")
        if isinstance(ai_tags, str):
            try:
                ai_tags = json.loads(ai_tags)
            except Exception:
                ai_tags = []
        elif not isinstance(ai_tags, list):
            ai_tags = []

        return {
            "company_name": row.get("company_name", ""),
            "official_domain": row.get("official_domain", ""),
            "wikipedia_summary": row.get("wikipedia_summary", ""),
            "github_org": row.get("github_org", ""),
            "tech_stack": tech_stack,
            "open_roles": open_roles,
            "funding_stage": row.get("funding_stage", ""),
            "ai_focus_tags": ai_tags,
            "researched_at": row.get("researched_at", ""),
            "expires_at": row.get("expires_at", ""),
        }

