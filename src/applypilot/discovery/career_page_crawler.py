"""Live Career Page Crawler using Headed Playwright on Dedicated Hyprland Workspace.

Discovers company career portals (Greenhouse, Lever, Ashby, Workday, or direct careers domains),
launches headed Chromium maximized on dedicated Arch Linux Hyprland Workspace 11,
extracts real-time job openings via JSON-LD and DOM heuristics, captures visual screenshot proofs,
and permanently persists all discovered jobs to SQLite.
"""

from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
import sqlite3

from applypilot import config
from applypilot.database import (
    get_connection,
    store_jobs,
    upsert_career_watchlist,
    get_company_intel,
    save_company_intel,
)
from applypilot.system.hyprland_controller import HyprlandController

logger = logging.getLogger("applypilot.career_crawler")

TECH_ROLES_PATTERN = re.compile(
    r"\b(software|engineer|engineering|developer|architect|tech lead|ai|ml|machine learning|"
    r"deep learning|nlp|data engineer|full stack|backend|frontend|devops|sre|platform|infrastructure|"
    r"applied scientist|research scientist|distributed systems|robotics)\b",
    re.IGNORECASE,
)

CANDIDATE_SKILLS = [
    "Python", "FastAPI", "React", "Docker", "Kubernetes", "PyTorch", "TypeScript",
    "PostgreSQL", "Redis", "LangGraph", "LangChain", "LLM", "Agent", "AI", "Machine Learning",
    "Next.js", "Three.js", "GraphQL", "Playwright", "C++", "Rust"
]


def find_best_matching_job(
    jobs: list[dict[str, Any]] | None,
    candidate_keywords: list[str] | None = None,
) -> tuple[str | None, str | None]:
    """Find the single most relevant open job posting for the candidate from crawled roles.
    
    Returns (job_title, job_url).
    """
    if not jobs:
        return None, None

    keywords = [k.lower() for k in (candidate_keywords or [
        "full stack", "fullstack", "software engineer", "frontend", "backend",
        "ai engineer", "founding", "python", "react", "systems"
    ])]

    scored: list[tuple[int, str, str]] = []
    for j in jobs:
        title = (j.get("title") or "").strip()
        url = (j.get("url") or "").strip()
        if not title:
            continue
        t_lower = title.lower()
        score = 0
        for idx, kw in enumerate(keywords):
            if kw in t_lower:
                score += (len(keywords) - idx) * 2
        scored.append((score, title, url))

    if scored:
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1], scored[0][2]

    # Fallback to first role
    first = jobs[0]
    return first.get("title"), first.get("url")


class CareerPageCrawler:
    """Discovers and scrapes real-time career portals with headed visual execution on Hyprland Workspace 11."""

    def __init__(
        self,
        workspace: int = 11,
        headless: bool = False,
        conn: sqlite3.Connection | None = None,
        dwell_time: float = 4.0,
    ) -> None:
        self.workspace = workspace
        self.headless = headless
        self.conn = conn
        self.dwell_time = dwell_time
        self.hypr = HyprlandController(workspace=workspace)

    def resolve_career_url(self, company_name: str, domain: str | None = None) -> tuple[str | None, str]:
        """Find the most likely active career portal for a company.
        
        Returns: (career_url, ats_provider)
        """
        c_name = (company_name or "").strip()
        c_domain = (domain or "").strip().lower()
        conn = self.conn or get_connection()

        # 1. Check existing watchlist entry
        try:
            row = conn.execute(
                """
                SELECT careers_page_url, ats_provider, ats_board_token, official_domain 
                FROM career_watchlist 
                WHERE LOWER(company_name) = LOWER(?) OR (? != '' AND LOWER(official_domain) = LOWER(?))
                LIMIT 1
                """,
                (c_name, c_domain, c_domain),
            ).fetchone()
            if row and row[0]:
                return row[0], row[1] or "custom"
        except Exception as e:
            logger.debug("Watchlist resolution lookup error: %s", e)

        # 2. Check if domain itself indicates an ATS
        if c_domain:
            if "greenhouse.io" in c_domain:
                slug = c_domain.split(".")[0]
                return f"https://boards.greenhouse.io/{slug}", "greenhouse"
            if "lever.co" in c_domain:
                slug = c_domain.split(".")[0]
                return f"https://jobs.lever.co/{slug}", "lever"
            if "ashbyhq.com" in c_domain:
                slug = c_domain.split(".")[0]
                return f"https://jobs.ashbyhq.com/{slug}", "ashby"
            if "myworkdayjobs.com" in c_domain:
                return f"https://{c_domain}", "workday"

        # 3. Standard corporate domain heuristics
        if c_domain:
            # Common subdomains
            clean_dom = re.sub(r"^www\.", "", c_domain)
            return f"https://careers.{clean_dom}", "custom"

        # 4. Fallback search probe URL
        slug = re.sub(r"[^a-zA-Z0-9]", "", c_name).lower()
        return f"https://boards.greenhouse.io/{slug}", "greenhouse"

    async def crawl_live_careers(
        self,
        company_name: str,
        domain: str | None = None,
        max_jobs: int = 15,
    ) -> dict[str, Any]:
        """Execute live headed Playwright crawl on Hyprland Workspace 11.
        
        Extracts real-time jobs, captures visual proofs, highlights matching skills,
        and saves all newly discovered roles directly into SQLite.
        """
        from playwright.async_api import async_playwright

        c_name = (company_name or "").strip()
        c_domain = (domain or "").strip().lower()
        career_url, ats_provider = self.resolve_career_url(c_name, c_domain)

        logger.info(
            "🚀 [Career Crawler] Launching headed Playwright on Workspace %d for '%s' (Portal: %s)",
            self.workspace, c_name, career_url
        )

        # Notify user on desktop (Wayland/Hyprland)
        self.hypr.notify(
            f"ApplyPilot Crawler: {c_name}",
            f"Inspecting live career portal on Workspace {self.workspace} (Resolution: 2560x1440)",
        )

        discovered_jobs: list[dict[str, Any]] = []
        screenshot_path: str | None = None
        conn = self.conn or get_connection()

        # Path 1: Check ATS Direct API Fast-Path for Greenhouse / Lever / Ashby
        api_jobs = await self._try_ats_api(c_name, c_domain, ats_provider)
        if api_jobs:
            logger.info("   ├─ [ATS API Fast-Path] Successfully extracted %d live postings directly", len(api_jobs))
            discovered_jobs.extend(api_jobs)

        # Path 2: Headed Playwright on Workspace 11 for Visual Inspection & Proof
        launch_cfg = self.hypr.get_playwright_launch_config(headless=self.headless)
        proofs_dir = config.PROOFS_DIR / "careers"
        proofs_dir.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-zA-Z0-9_-]", "_", c_name).lower()[:30] or "company"
        ss_file = proofs_dir / f"{slug}_{int(time.time())}.png"

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=launch_cfg["headless"],
                    args=launch_cfg["args"],
                )
                context = await browser.new_context(
                    viewport=launch_cfg["viewport"],
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                )
                page = await context.new_page()

                # Navigate to career page
                target_url = career_url or f"https://{c_domain}/careers"
                try:
                    logger.info("   ├─ [Workspace %d] Loading %s...", self.workspace, target_url)
                    await page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
                    await asyncio.sleep(2.0)  # Allow initial page render
                except Exception as e:
                    logger.warning("   ├─ Initial portal navigation notice for %s: %s", target_url, e)
                    # Try secondary fallback to domain/jobs
                    if c_domain and "careers." in target_url:
                        alt_url = f"https://{c_domain}/careers"
                        try:
                            await page.goto(alt_url, wait_until="domcontentloaded", timeout=15000)
                            target_url = alt_url
                        except Exception:
                            pass

                # Deep Navigation: If on landing page or base domain, find and follow career portal link
                try:
                    career_link = await page.evaluate("""
                    () => {
                        const keywords = ['career', 'careers', 'join us', 'work with us', 'jobs', 'openings', 'hiring', 'we are hiring'];
                        const links = Array.from(document.querySelectorAll('a[href]'));
                        // Priority 1: Exact/contained text match
                        for (const a of links) {
                            const text = (a.innerText || a.textContent || '').trim().toLowerCase();
                            const href = (a.getAttribute('href') || '').trim();
                            if (!href || href.startsWith('#') || href.startsWith('javascript:')) continue;
                            for (const kw of keywords) {
                                if (text === kw || (text.length < 35 && text.includes(kw))) {
                                    try {
                                        return new URL(href, window.location.href).href;
                                    } catch(e) {}
                                }
                            }
                        }
                        // Priority 2: Match href path
                        for (const a of links) {
                            const href = (a.getAttribute('href') || '').trim();
                            for (const kw of ['/careers', '/jobs', '/openings', 'greenhouse.io', 'lever.co', 'ashbyhq.com']) {
                                if (href.toLowerCase().includes(kw)) {
                                    try {
                                        return new URL(href, window.location.href).href;
                                    } catch(e) {}
                                }
                            }
                        }
                        return null;
                    }
                    """)
                    if career_link and career_link != page.url and not page.url.rstrip('/').endswith(('/careers', '/jobs')):
                        logger.info("   ├─ [Deep Portal Navigation] Discovered career link in DOM: %s", career_link)
                        try:
                            await page.goto(career_link, wait_until="domcontentloaded", timeout=20000)
                            target_url = career_link
                            career_url = career_link
                            await asyncio.sleep(2.0)
                        except Exception as e:
                            logger.debug("Failed following discovered career link: %s", e)
                except Exception:
                    pass

                # Smooth auto-scroll to hydrate dynamic listings and provide visual observation
                try:
                    await page.evaluate("""
                    async () => {
                        await new Promise((resolve) => {
                            let totalHeight = 0;
                            const distance = 300;
                            const timer = setInterval(() => {
                                const scrollHeight = document.body.scrollHeight;
                                window.scrollBy(0, distance);
                                totalHeight += distance;
                                if (totalHeight >= Math.min(scrollHeight, 2500)) {
                                    clearInterval(timer);
                                    resolve();
                                }
                            }, 200);
                        });
                    }
                    """)
                except Exception:
                    pass

                # Highlight matching candidate skills on the live page
                try:
                    highlight_script = f"""
                    (() => {{
                        const skills = {json.dumps(CANDIDATE_SKILLS)};
                        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                        const nodes = [];
                        while (walker.nextNode()) nodes.push(walker.currentNode);
                        for (const node of nodes) {{
                            let text = node.nodeValue;
                            let replaced = false;
                            for (const skill of skills) {{
                                const regex = new RegExp(`\\\\b(${{skill}})\\\\b`, 'gi');
                                if (regex.test(text)) {{
                                    replaced = true;
                                    const span = document.createElement('span');
                                    span.innerHTML = text.replace(regex, '<mark style="background:#fef08a;color:#854d0e;padding:1px 3px;border-radius:3px;font-weight:bold;">$1</mark>');
                                    if (node.parentNode) {{
                                        node.parentNode.replaceChild(span, node);
                                    }}
                                    break;
                                }}
                            }}
                        }}
                    }})();
                    """
                    await page.evaluate(highlight_script)
                except Exception:
                    pass

                # Capture full-page visual screenshot proof
                try:
                    await page.screenshot(path=str(ss_file), full_page=False)
                    screenshot_path = str(ss_file)
                    logger.info("   ├─ [Visual Proof Captured] %s (Workspace %d)", ss_file.name, self.workspace)
                except Exception as e:
                    logger.debug("Screenshot capture error: %s", e)

                # Extract JSON-LD JobPosting schema from DOM
                dom_json_ld = await self._extract_json_ld_jobs(page, c_name)
                if dom_json_ld:
                    logger.info("   ├─ [JSON-LD Scraper] Found %d structured postings in page metadata", len(dom_json_ld))
                    discovered_jobs.extend(dom_json_ld)

                # Extract Job Links & Cards from DOM
                dom_card_jobs = await self._extract_dom_card_jobs(page, c_name, target_url)
                if dom_card_jobs:
                    logger.info("   ├─ [DOM Heuristics] Extracted %d potential tech roles from page links", len(dom_card_jobs))
                    discovered_jobs.extend(dom_card_jobs)

                # Visual Dwell Time: keep visible so user can observe matches on screen
                if self.dwell_time > 0 and not self.headless:
                    logger.info("   ├─ [Visual Inspection] Pausing %.1fs on Workspace %d for review...", self.dwell_time, self.workspace)
                    await asyncio.sleep(self.dwell_time)

                await browser.close()

        except Exception as e:
            logger.error("Career crawl Playwright execution error on Workspace %d: %s", self.workspace, e)

        # Deduplicate jobs by URL and Title
        unique_jobs: list[dict[str, Any]] = []
        seen_keys: set[str] = set()

        for j in discovered_jobs:
            key = f"{j.get('title', '').strip().lower()}::{j.get('url', '').strip()}"
            if key not in seen_keys:
                seen_keys.add(key)
                unique_jobs.append(j)

        # Filter and rank for tech relevance
        relevant_jobs = [j for j in unique_jobs if TECH_ROLES_PATTERN.search(j.get("title", ""))][:max_jobs]
        if not relevant_jobs and unique_jobs:
            # Fallback to general roles if no specific engineering keyword in title
            relevant_jobs = unique_jobs[:max_jobs]

        # -------------------------------------------------------------
        # PERMANENT PERSISTENCE: Never delete info, save all records!
        # -------------------------------------------------------------
        if relevant_jobs:
            now_iso = datetime.now(timezone.utc).isoformat()
            # 1. Save all discovered roles to `jobs` table with company populated
            for j in relevant_jobs:
                u = j.get("url")
                if not u:
                    continue
                try:
                    conn.execute(
                        """
                        INSERT INTO jobs (url, title, company, salary, description, location, site, strategy, discovered_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(url) DO UPDATE SET
                            company = COALESCE(excluded.company, jobs.company),
                            title = COALESCE(excluded.title, jobs.title)
                        """,
                        (
                            u,
                            j.get("title"),
                            c_name,
                            j.get("salary"),
                            j.get("description"),
                            j.get("location"),
                            f"careers_{ats_provider}",
                            "live_playwright_crawler",
                            now_iso,
                        ),
                    )
                except Exception as e:
                    logger.debug("Job insert error: %s", e)
            conn.commit()
            logger.info("   ├─ [DB Persistence: jobs] Persisted %d live jobs for %s into database", len(relevant_jobs), c_name)

            # 2. Update `career_watchlist`
            upsert_career_watchlist(
                company_name=c_name,
                official_domain=c_domain,
                careers_page_url=career_url,
                ats_provider=ats_provider,
                open_roles_count=len(relevant_jobs),
                conn=conn,
            )
            logger.info(
                "   ├─ [DB Persistence: career_watchlist] Updated %s (ATS: %s, Open roles: %d)",
                c_name, ats_provider, len(relevant_jobs)
            )

            # 3. Update `company_intel` with newly extracted live roles
            cached_intel = get_company_intel(c_domain or c_name.lower(), conn=conn) or {}
            cached_intel["open_roles_json"] = relevant_jobs
            cached_intel["official_domain"] = c_domain
            cached_intel["company_name"] = c_name
            cached_intel["domain_or_name"] = c_domain or c_name.lower()
            now_iso = datetime.now(timezone.utc).isoformat()
            if not cached_intel.get("researched_at"):
                cached_intel["researched_at"] = now_iso
            cached_intel["expires_at"] = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
            
            save_company_intel(cached_intel, conn=conn)
            logger.info("   └─ [DB Persistence: company_intel] Synced %d live roles into 30-day cache", len(relevant_jobs))

        best_title, best_url = find_best_matching_job(relevant_jobs)
        return {
            "company_name": c_name,
            "domain": c_domain,
            "career_url": career_url,
            "ats_provider": ats_provider,
            "total_extracted": len(relevant_jobs),
            "jobs": relevant_jobs,
            "best_matching_job_title": best_title,
            "best_matching_job_url": best_url,
            "screenshot_path": screenshot_path,
        }

    async def _try_ats_api(self, company_name: str, domain: str, ats_provider: str) -> list[dict[str, Any]]:
        """Query public ATS endpoints for Greenhouse, Lever, and Ashby."""
        results: list[dict[str, Any]] = []
        slug = domain.split(".")[0] if domain else re.sub(r"[^a-zA-Z0-9]", "", company_name).lower()

        # Greenhouse Public API
        if ats_provider == "greenhouse" or not ats_provider or ats_provider == "custom":
            try:
                gh_url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
                req = urllib.request.Request(gh_url, headers={"User-Agent": "ApplyPilot/1.0"})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        for item in data.get("jobs", []):
                            results.append({
                                "title": item.get("title", ""),
                                "url": item.get("absolute_url", ""),
                                "location": item.get("location", {}).get("name", "Remote"),
                                "company": company_name,
                                "salary": None,
                                "description": f"Greenhouse role: {item.get('title')}",
                            })
                        if results:
                            return results
            except Exception:
                pass

        # Lever Public API
        if ats_provider == "lever" or not results:
            try:
                lev_url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
                req = urllib.request.Request(lev_url, headers={"User-Agent": "ApplyPilot/1.0"})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        for item in data:
                            results.append({
                                "title": item.get("text", ""),
                                "url": item.get("hostedUrl", ""),
                                "location": item.get("categories", {}).get("location", "Remote"),
                                "company": company_name,
                                "salary": None,
                                "description": f"Lever role: {item.get('text')}",
                            })
                        if results:
                            return results
            except Exception:
                pass

        # Ashby Public API
        if ats_provider == "ashby" or not results:
            try:
                ash_url = f"https://jobs.ashbyhq.com/api/non-authenticated/jobs?jobBoardName={slug}"
                req = urllib.request.Request(ash_url, headers={"User-Agent": "ApplyPilot/1.0"})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        for item in data.get("jobs", []):
                            results.append({
                                "title": item.get("title", ""),
                                "url": f"https://jobs.ashbyhq.com/{slug}/{item.get('id')}",
                                "location": item.get("locationName", "Remote"),
                                "company": company_name,
                                "salary": None,
                                "description": f"Ashby role: {item.get('title')}",
                            })
                        if results:
                            return results
            except Exception:
                pass

        return results

    async def _extract_json_ld_jobs(self, page: Any, company_name: str) -> list[dict[str, Any]]:
        """Extract schema.org JobPosting objects from page JSON-LD scripts."""
        jobs: list[dict[str, Any]] = []
        try:
            scripts = await page.eval_on_selector_all(
                'script[type="application/ld+json"]',
                "elements => elements.map(e => e.innerText)"
            )
            for raw in scripts:
                try:
                    data = json.loads(raw)
                    items = data if isinstance(data, list) else [data]
                    for it in items:
                        if isinstance(it, dict) and it.get("@type") == "JobPosting":
                            jobs.append({
                                "title": it.get("title", ""),
                                "url": it.get("url") or page.url,
                                "location": str(it.get("jobLocation", "Remote")),
                                "salary": str(it.get("baseSalary", "")),
                                "description": it.get("description", "")[:400],
                                "company": company_name,
                            })
                except Exception:
                    continue
        except Exception as e:
            logger.debug("JSON-LD evaluation error: %s", e)
        return jobs

    async def _extract_dom_card_jobs(self, page: Any, company_name: str, base_url: str) -> list[dict[str, Any]]:
        """Extract job listings from DOM link elements and anchors."""
        jobs: list[dict[str, Any]] = []
        try:
            links = await page.eval_on_selector_all(
                "a[href]",
                """elements => elements.map(a => ({
                    text: a.innerText.trim(),
                    href: a.getAttribute('href')
                }))"""
            )
            for item in links:
                text = item.get("text", "")
                href = item.get("href", "")
                if not text or not href:
                    continue
                # Check if text matches tech roles pattern
                if len(text) < 80 and TECH_ROLES_PATTERN.search(text):
                    abs_url = urllib.parse.urljoin(base_url, href)
                    jobs.append({
                        "title": text,
                        "url": abs_url,
                        "location": "Remote / Office",
                        "salary": None,
                        "description": f"Open position at {company_name}: {text}",
                        "company": company_name,
                    })
        except Exception as e:
            logger.debug("DOM link evaluation error: %s", e)
        return jobs


def crawl_company_careers_sync(
    company_name: str,
    domain: str | None = None,
    workspace: int = 11,
    headless: bool = False,
    conn: sqlite3.Connection | None = None,
    dwell_time: float = 4.0,
) -> dict[str, Any]:
    """Synchronous convenience wrapper to execute career crawl."""
    crawler = CareerPageCrawler(workspace=workspace, headless=headless, conn=conn, dwell_time=dwell_time)
    return asyncio.run(crawler.crawl_live_careers(company_name, domain))
