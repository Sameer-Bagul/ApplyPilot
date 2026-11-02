"""Part 1 Omni-Channel Discovery Orchestrator.

Combines Reddit scraping, social search dorks, and direct ATS career feeds.
Parses candidates with zero-token regex extraction, applies career resolver,
assigns execution routes (EMAIL_ONLY, PORTAL_ONLY, DUAL_ATTACK), and saves
leads to recruiter_leads and jobs.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
from typing import Any

from applypilot import config
from applypilot.discovery.ats_direct_feeds import poll_watchlist
from applypilot.discovery.company_resolver import resolve_company_ats
from applypilot.database import (
    get_career_watchlist,
    get_connection,
    store_recruiter_lead,
)
from applypilot.discovery.social_dorker import run_social_dorks
from applypilot.discovery.lead_extractor import (
    classify_execution_route,
    parse_social_post,
)
from applypilot.discovery.hackernews_harvester import scrape_hn_hiring_posts
from applypilot.discovery.reddit_scraper import scrape_reddit_hiring_posts

logger = logging.getLogger(__name__)


def run_omni_channel_discovery(
    sources: list[str] | None = None,
    role_keywords: list[str] | None = None,
    dry_run: bool = False,
    limit: int = 50,
    conn: sqlite3.Connection | None = None,
    extra_posts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Execute daily omni-channel discovery across social posts and career boards.

    Args:
        sources: List of sources to query (['hn', 'reddit', 'dorks', 'watchlist']).
        role_keywords: Target role keywords for search dorks.
        dry_run: If True, only preview discovered items without saving to DB.
        limit: Max items to process per channel.
        conn: Optional SQLite connection.
        extra_posts: Optional extra posts (e.g. FreeHire catalogue jobs).

    Returns:
        Summary dict of discovered leads and jobs by execution route and source.
    """
    if conn is None and not dry_run:
        conn = get_connection()

    selected_sources = set(sources or ["hn", "reddit", "dorks", "watchlist"])
    discovered_leads: list[dict[str, Any]] = []
    discovered_jobs: list[dict[str, Any]] = []
    route_counts = {"EMAIL_ONLY": 0, "PORTAL_ONLY": 0, "DUAL_ATTACK": 0, "UNKNOWN": 0}
    source_stats: dict[str, dict[str, int]] = {}

    def _track_stat(source_name: str, key: str, inc: int = 1) -> None:
        if source_name not in source_stats:
            source_stats[source_name] = {"posts": 0, "jobs": 0, "emails": 0}
        source_stats[source_name][key] = source_stats[source_name].get(key, 0) + inc

    # 1. Hacker News Who is Hiring
    hn_posts: list[dict[str, Any]] = []
    if "hn" in selected_sources:
        try:
            hn_posts = scrape_hn_hiring_posts(max_threads=1, max_comments_per_thread=limit)
            _track_stat("hackernews", "posts", len(hn_posts))
        except Exception as e:
            logger.warning("HN scraping warning: %s", e)

    # 2. Reddit .json hiring feeds
    reddit_posts: list[dict[str, Any]] = []
    if "reddit" in selected_sources:
        try:
            reddit_posts = scrape_reddit_hiring_posts(limit_per_sub=min(limit, 30))
            _track_stat("reddit", "posts", len(reddit_posts))
        except Exception as e:
            logger.warning("Reddit scraping warning: %s", e)

    # 3. Time-bounded social search dorks (LinkedIn, X, Threads)
    dork_posts: list[dict[str, Any]] = []
    if "dorks" in selected_sources:
        try:
            dork_posts = run_social_dorks(role_keywords=role_keywords, max_results_per_dork=min(limit, 10))
            _track_stat("search_dorks", "posts", len(dork_posts))
        except Exception as e:
            logger.warning("Search dorks warning: %s", e)

    # Combine social posts
    all_social_posts = hn_posts + reddit_posts + dork_posts + (extra_posts or [])

    for post in all_social_posts:
        title = post.get("title", "")
        text = post.get("text", "")
        url = post.get("url", "")
        platform = post.get("platform", "social")

        parsed = parse_social_post(title, text, source_url=url, platform=platform)
        email = parsed.get("primary_email")
        ats_url = parsed.get("primary_ats_url")
        route = parsed.get("execution_route", "UNKNOWN")
        company = parsed.get("company_name")

        # If post mentions company but lacks ATS URL, try career resolver
        if not ats_url and company:
            try:
                res = resolve_company_ats(company)
                if res.get("resolved_ats_url"):
                    ats_url = res["resolved_ats_url"]
                    parsed["primary_ats_url"] = ats_url
                    route = classify_execution_route(has_email=bool(email), has_portal_url=True)
                    parsed["execution_route"] = route
            except Exception:
                pass

        route_counts[route] = route_counts.get(route, 0) + 1

        # Determine Job ID or canonical URL
        job_url = ats_url or url
        role_title = title[:80] or "Software Engineer"
        lead_item = {
            "contact_email": email,
            "role_title": role_title,
            "company_name": company,
            "source_platform": platform,
            "source_post_url": url,
            "evidence_snippet": parsed.get("evidence_snippet", ""),
            "execution_route": route,
            "contact_type": parsed.get("contact_type", "recruiter"),
            "primary_ats_url": ats_url,
        }

        if email:
            discovered_leads.append(lead_item)
            _track_stat(platform, "emails", 1)
            if not dry_run and conn:
                store_recruiter_lead(
                    contact_email=email,
                    role_title=role_title,
                    company_name=company,
                    source_platform=platform,
                    source_post_url=url,
                    evidence_snippet=parsed.get("evidence_snippet", ""),
                    execution_route=route,
                    contact_type=parsed.get("contact_type", "recruiter"),
                    conn=conn,
                )

        if ats_url:
            job_item = {
                "url": ats_url,
                "title": role_title,
                "company": company or "Unknown",
                "site": platform,
                "execution_route": route,
                "description": text[:500],
            }
            discovered_jobs.append(job_item)
            _track_stat(platform, "jobs", 1)
            if not dry_run and conn:
                try:
                    conn.execute(
                        """
                        INSERT INTO jobs (url, title, company, site, description, execution_route, state)
                        VALUES (?, ?, ?, ?, ?, ?, 'discovered')
                        ON CONFLICT(url) DO UPDATE SET
                            execution_route = COALESCE(excluded.execution_route, jobs.execution_route),
                            title = COALESCE(excluded.title, jobs.title)
                        """,
                        (ats_url, role_title, company or "Unknown", platform, text[:500], route),
                    )
                    conn.commit()
                except Exception as e:
                    logger.debug("Job insert notice: %s", e)

    # 4. Direct ATS career feeds from Watchlist
    watchlist_jobs: list[dict[str, Any]] = []
    if "watchlist" in selected_sources and conn:
        try:
            wl = get_career_watchlist(conn=conn)
            if wl:
                watchlist_jobs = poll_watchlist(wl)
                _track_stat("career_watchlist", "posts", len(wl))
                _track_stat("career_watchlist", "jobs", len(watchlist_jobs))
                for wj in watchlist_jobs:
                    route_counts["PORTAL_ONLY"] += 1
                    discovered_jobs.append(wj)
                    if not dry_run and conn:
                        try:
                            conn.execute(
                                """
                                INSERT INTO jobs (url, title, company, site, location, description, execution_route, state)
                                VALUES (?, ?, ?, ?, ?, ?, 'PORTAL_ONLY', 'discovered')
                                ON CONFLICT(url) DO UPDATE SET
                                    execution_route = 'PORTAL_ONLY'
                                """,
                                (
                                    wj["url"],
                                    wj.get("title", "Role"),
                                    wj.get("company", "Company"),
                                    wj.get("site", "ats"),
                                    wj.get("location", "Remote"),
                                    wj.get("description", "")[:500],
                                ),
                            )
                            conn.commit()
                        except Exception as e:
                            logger.debug("Watchlist job insert notice: %s", e)
        except Exception as e:
            logger.warning("Watchlist poll warning: %s", e)

    total = len(discovered_leads) + len(discovered_jobs)
    return {
        "total_discovered": total,
        "hn_posts_count": len(hn_posts),
        "reddit_posts_count": len(reddit_posts),
        "dork_posts_count": len(dork_posts),
        "watchlist_jobs_count": len(watchlist_jobs),
        "leads_count": len(discovered_leads),
        "jobs_count": len(discovered_jobs),
        "route_counts": route_counts,
        "source_breakdown": source_stats,
        "discovered_leads": discovered_leads,
        "discovered_jobs": discovered_jobs,
        "sample_leads": discovered_leads[:5],
        "sample_jobs": discovered_jobs[:5],
        "dry_run": dry_run,
    }
