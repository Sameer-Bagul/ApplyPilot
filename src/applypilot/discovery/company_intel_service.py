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

    def __init__(
        self,
        conn: sqlite3.Connection | None = None,
        workspace: int = 11,
        headless: bool = False,
        live_scrape: bool = False,
    ) -> None:
        self.conn = conn
        self.workspace = workspace
        self.headless = headless
        self.live_scrape = live_scrape

    def get_or_research(
        self,
        company_name: str,
        domain: str | None = None,
        force_refresh: bool = False,
        live_scrape: bool | None = None,
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

        should_crawl = self.live_scrape if live_scrape is None else live_scrape

        # 1. Check SQLite 30-day cache
        if not force_refresh:
            cached = get_company_intel(cache_key, conn=self.conn)
            if not cached and c_name:
                cached = get_company_intel(c_name.lower(), conn=self.conn)

            if cached:
                intel_dict = self._format_intel_dict(cached)
                # If cached but user explicitly requested live crawl and no roles cached, allow live crawl
                if should_crawl and not intel_dict.get("open_roles"):
                    logger.info("🔍 [Live Scrape Triggered] Cached intel has 0 roles for '%s'; crawling live careers on Workspace %d...", c_name, self.workspace)
                else:
                    logger.info(
                        "⚡ [Cache Hit] Reusing 30-day cached intel for '%s' (domain: %s) -> Stack: %s | AI Tags: %s | Roles: %d",
                        c_name, c_domain, intel_dict.get("tech_stack", [])[:5], intel_dict.get("ai_focus_tags", []), len(intel_dict.get("open_roles", []))
                    )
                    return intel_dict

        # 2. Cache miss -> Perform fresh investigation
        logger.info("🔎 [Online OSINT] Researching company '%s' (domain: %s)...", c_name, c_domain)
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
            if local_jobs:
                logger.info("   ├─ Local Jobs DB: Matched %d active job openings for %s", len(local_jobs), c_name)
        except Exception as e:
            logger.debug("Local jobs lookup error for %s: %s", c_name, e)

        # (a2) Live Headed Playwright Scrape on Hyprland Workspace 11
        if should_crawl:
            try:
                from applypilot.discovery.career_page_crawler import crawl_company_careers_sync
                crawl_res = crawl_company_careers_sync(
                    company_name=c_name,
                    domain=c_domain,
                    workspace=self.workspace,
                    headless=self.headless,
                    conn=conn,
                )
                live_roles = crawl_res.get("jobs", [])
                if live_roles:
                    local_jobs = live_roles + local_jobs
                    logger.info("   ├─ [Live Career Scrape] Workspace %d added %d live positions", self.workspace, len(live_roles))
            except Exception as e:
                logger.debug("Live career crawler error for %s: %s", c_name, e)

        # (b) Query Wikipedia REST API
        wiki_summary = ""
        wiki_founders: list[str] = []
        try:
            wiki_res = investigate_company_wikipedia(c_name)
            if wiki_res.get("found"):
                wiki_summary = wiki_res.get("summary", "")
                logger.info("   ├─ Wikipedia: Found %d-char summary (%s)", len(wiki_summary), wiki_summary[:60] + "...")
            else:
                logger.info("   ├─ Wikipedia: No Wikipedia entry found for %s", c_name)
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
                logger.info("   ├─ GitHub Org (%s): Found %d public repos, detected tech stack: %s", slug, len(gh_repos), list(tech_stack) if tech_stack else 'None')
            else:
                logger.info("   ├─ GitHub Org (%s): No public repositories found", slug)
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
        if ai_tags:
            logger.info("   ├─ AI Focus Vectors: %s", ai_tags)

        # (f) Discover key personnel & LinkedIn profiles (non-login OSINT)
        key_people: list[dict[str, Any]] = []
        try:
            from applypilot.discovery.linkedin_people_finder import find_company_people_sync
            key_people = find_company_people_sync(
                company_name=c_name,
                domain=c_domain,
                conn=conn,
            )
            if key_people:
                logger.info("   ├─ [LinkedIn OSINT] Harvested %d leadership profiles for %s", len(key_people), c_name)
        except Exception as e:
            logger.debug("LinkedIn people finder error for %s: %s", c_name, e)

        # (g) Deep Web Searcher for Page 1 & 2 organic articles & milestones
        observed_emails: list[str] = []
        try:
            from applypilot.discovery.deep_web_searcher import DeepWebSearcher
            searcher = DeepWebSearcher()
            deep_web_data = searcher.search_and_analyze_company(c_name, domain=c_domain)
            observed_emails.extend(deep_web_data.get("discovered_emails", []))
            for m in deep_web_data.get("company_milestones", []):
                if m not in wiki_summary:
                    wiki_summary = f"{wiki_summary} {m}".strip()
        except Exception as e:
            logger.debug("Deep web searcher notice for %s: %s", c_name, e)

        # (h) Social Hiring Harvester for LinkedIn & X Posts
        hiring_posts: list[dict[str, Any]] = []
        try:
            from applypilot.discovery.social_hiring_harvester import SocialHiringHarvester
            social_harvester = SocialHiringHarvester(conn=conn)
            hiring_posts = social_harvester.harvest_company_hiring_posts(c_name, domain=c_domain)
            if hiring_posts:
                social_harvester.persist_posts_to_leads(hiring_posts, c_name, c_domain, conn=conn)
                for hp in hiring_posts:
                    observed_emails.extend(hp.get("embedded_emails", []))
                logger.info("   ├─ [Social Hiring] Harvested %d public hiring posts for %s", len(hiring_posts), c_name)
        except Exception as e:
            logger.debug("Social hiring harvester notice for %s: %s", c_name, e)

        # (i) Deduce Corporate Email Pattern & Apply to Key Leadership
        detected_pattern = "{first}.{last}"
        pattern_confidence = 0.60
        try:
            from applypilot.discovery.email_pattern_engine import EmailPatternEngine
            pattern_engine = EmailPatternEngine()
            pattern_res = pattern_engine.deduce_pattern(observed_emails, sample_people=key_people, domain=c_domain)
            detected_pattern = pattern_res.get("pattern", "{first}.{last}")
            pattern_confidence = pattern_res.get("confidence", 0.60)
            logger.info("   ├─ [Email Pattern] Deduced '%s' (confidence: %.2f) from %d emails", detected_pattern, pattern_confidence, len(observed_emails))

            if key_people:
                key_people = pattern_engine.apply_pattern_to_people(key_people, domain=c_domain or c_name.lower(), pattern=detected_pattern, confidence=pattern_confidence)
        except Exception as e:
            logger.debug("Email pattern deduction notice for %s: %s", c_name, e)

        # (j) Persist to company_intel
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
            "key_people_json": key_people,
            "detected_email_pattern": detected_pattern,
            "email_pattern_confidence": pattern_confidence,
            "hiring_posts_json": hiring_posts,
            "researched_at": now.isoformat(),
            "expires_at": expires.isoformat(),
        }

        try:
            save_company_intel(intel_record, conn=conn)
            logger.info("   └─ Stored in SQLite 'company_intel' table (30-day cache until %s)", expires.strftime("%Y-%m-%d"))
        except Exception as e:
            logger.warning("Failed saving company_intel for %s: %s", cache_key, e)

        return self._format_intel_dict(intel_record)

    def enrich_batch_for_leads(
        self,
        leads: list[dict[str, Any]],
        force_refresh: bool = False,
        live_scrape: bool | None = None,
    ) -> dict[str, dict[str, Any]]:
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
            intel = self.get_or_research(
                c_name,
                domain=domain,
                force_refresh=force_refresh,
                live_scrape=live_scrape,
            )
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

        key_people = row.get("key_people_json")
        if isinstance(key_people, str):
            try:
                key_people = json.loads(key_people)
            except Exception:
                key_people = []
        elif not isinstance(key_people, list):
            key_people = []

        hiring_posts = row.get("hiring_posts_json")
        if isinstance(hiring_posts, str):
            try:
                hiring_posts = json.loads(hiring_posts)
            except Exception:
                hiring_posts = []
        elif not isinstance(hiring_posts, list):
            hiring_posts = []

        return {
            "company_name": row.get("company_name", ""),
            "official_domain": row.get("official_domain", ""),
            "wikipedia_summary": row.get("wikipedia_summary", ""),
            "github_org": row.get("github_org", ""),
            "tech_stack": tech_stack,
            "open_roles": open_roles,
            "funding_stage": row.get("funding_stage", ""),
            "ai_focus_tags": ai_tags,
            "key_people": key_people,
            "detected_email_pattern": row.get("detected_email_pattern"),
            "email_pattern_confidence": float(row.get("email_pattern_confidence") or 0.0),
            "hiring_posts": hiring_posts,
            "researched_at": row.get("researched_at", ""),
            "expires_at": row.get("expires_at", ""),
        }

