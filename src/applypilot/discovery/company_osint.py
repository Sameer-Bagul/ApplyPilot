"""Company OSINT & Intelligence Investigation Engine.

Provides deep background investigation on companies, their engineering projects,
tech stack, and multi-tier email discovery (including corporate and personal emails).

Integrates:
1. Wikipedia & Wikidata REST API (Zero-token company background, executives, products)
2. GitHub Organization & Tech Radar (Open source repos, frameworks, and projects)
3. GitHub Commit Author Personal Email Extractor (Discovers @gmail.com from git commits)
4. Fast Lightweight Scraper with Playwright fallback
"""

from __future__ import annotations

import json
import logging
import re
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger("applypilot.osint")

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
GENERIC_DOMAINS = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "proton.me", "protonmail.com"}


def investigate_company_wikipedia(company_name: str, timeout: float = 6.0) -> dict[str, Any]:
    """Retrieve verified company background, founders, and products via Wikipedia REST API."""
    cleaned = re.sub(r"\b(Inc|LLC|Ltd|Pvt|Corp|Corporation|Technologies|Solutions)\b", "", company_name, flags=re.IGNORECASE).strip()
    encoded = urllib.parse.quote(cleaned)
    url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts|pageprops&exintro=1&explaintext=1&titles={encoded}&format=json"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ApplyPilot-OSINT/2.0 (contact@applypilot.local)"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            pages = data.get("query", {}).get("pages", {})
            for pid, pdata in pages.items():
                if pid != "-1":
                    return {
                        "found": True,
                        "title": pdata.get("title"),
                        "summary": pdata.get("extract", "")[:1200],
                        "page_id": pid,
                        "source": "Wikipedia",
                    }
    except Exception as e:
        logger.debug("Wikipedia investigation notice: %s", e)

    return {"found": False, "summary": None}


def investigate_company_github_projects(company_slug: str, timeout: float = 6.0) -> list[dict[str, Any]]:
    """Discover company open-source projects, repositories, and tech stack via GitHub Org API."""
    clean_slug = company_slug.lower().replace(" ", "").replace("-", "")
    url = f"https://api.github.com/orgs/{clean_slug}/repos?sort=stars&per_page=6"

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ApplyPilot-OSINT/2.0",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            repos = json.loads(resp.read().decode("utf-8"))
            if isinstance(repos, list):
                return [
                    {
                        "name": r.get("name"),
                        "description": r.get("description"),
                        "language": r.get("language"),
                        "stars": r.get("stargazers_count", 0),
                        "forks": r.get("forks_count", 0),
                        "url": r.get("html_url"),
                    }
                    for r in repos[:6]
                ]
    except Exception as e:
        logger.debug("GitHub org investigation notice for %s: %s", company_slug, e)

    return []


def hunt_personal_emails_from_github(username: str, timeout: float = 6.0) -> list[str]:
    """Extract personal emails (e.g. @gmail.com) from a developer or recruiter's public git commits."""
    url = f"https://api.github.com/users/{username}/events/public"
    found_emails: set[str] = set()

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "ApplyPilot-OSINT/2.0",
                "Accept": "application/vnd.github.v3+json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            events = json.loads(resp.read().decode("utf-8"))
            if isinstance(events, list):
                for ev in events:
                    if ev.get("type") == "PushEvent":
                        commits = ev.get("payload", {}).get("commits", [])
                        for c in commits:
                            author = c.get("author", {})
                            em = author.get("email", "")
                            if em and "@" in em and not em.endswith("noreply.github.com"):
                                found_emails.add(em.lower())
    except Exception as e:
        logger.debug("GitHub commit email search notice for %s: %s", username, e)

    return sorted(list(found_emails))


def hunt_candidate_and_exec_emails(
    person_name: str,
    company_name: str,
    domain: str | None = None,
    github_handle: str | None = None,
) -> dict[str, Any]:
    """Execute multi-tier email OSINT to discover both Corporate and Personal email addresses."""
    results: dict[str, Any] = {
        "person_name": person_name,
        "company_name": company_name,
        "corporate_emails": [],
        "personal_emails": [],
        "sources_used": [],
    }

    # 1. Synthesize Corporate Email Patterns if domain is known
    parts = person_name.strip().split()
    first = parts[0].lower() if parts else ""
    last = parts[-1].lower() if len(parts) > 1 else ""

    if domain and first and last:
        clean_dom = domain.replace("http://", "").replace("https://", "").split("/")[0].lower()
        corporate_candidates = [
            f"{first}.{last}@{clean_dom}",
            f"{first}@{clean_dom}",
            f"{first[0]}{last}@{clean_dom}",
            f"{first}_{last}@{clean_dom}",
        ]
        results["corporate_emails"].extend(corporate_candidates)
        results["sources_used"].append("Corporate Pattern Synthesizer")

    # 2. Extract Personal Email from GitHub commit history if username is known or matches
    gh_user = github_handle or (f"{first}{last}" if first and last else None)
    if gh_user:
        gh_emails = hunt_personal_emails_from_github(gh_user)
        for em in gh_emails:
            domain_part = em.split("@")[-1].lower()
            if domain_part in GENERIC_DOMAINS:
                results["personal_emails"].append(em)
            else:
                results["corporate_emails"].append(em)
        if gh_emails:
            results["sources_used"].append("GitHub Public Commits OSINT")

    # 3. Web Search OSINT Dorks for Personal Emails
    try:
        from applypilot.discovery.dual_scraper import FastLightScraper
        scraper = FastLightScraper(timeout=4.0)
        query = f'"{person_name}" ("gmail.com" OR "proton.me") "{company_name}"'
        encoded_q = urllib.parse.quote(query)
        search_url = f"https://html.duckduckgo.com/html/?q={encoded_q}"
        fetch_res = scraper.fetch(search_url)
        if fetch_res.get("success"):
            text = fetch_res.get("text", "")
            raw_emails = EMAIL_REGEX.findall(text)
            for em in raw_emails:
                em_lower = em.lower()
                dom = em_lower.split("@")[-1]
                if dom in GENERIC_DOMAINS and not em_lower.startswith(("support@", "contact@", "help@", "info@")):
                    results["personal_emails"].append(em_lower)
            if any(em.split("@")[-1] in GENERIC_DOMAINS for em in raw_emails):
                results["sources_used"].append("Web Search OSINT Dorking")
    except Exception as e:
        logger.debug("Personal email search dork notice: %s", e)

    # Deduplicate
    results["corporate_emails"] = list(dict.fromkeys(results["corporate_emails"]))
    results["personal_emails"] = list(dict.fromkeys(results["personal_emails"]))

    return results


def investigate_and_store_company(
    company_name: str,
    conn: Any = None,
) -> dict[str, Any]:
    """Execute complete deep investigation on a company and persist to career_watchlist."""
    from datetime import datetime, timezone
    from applypilot.database import get_connection

    if conn is None:
        conn = get_connection()

    now = datetime.now(timezone.utc).isoformat()
    logger.info("Executing deep OSINT investigation on company: %s", company_name)

    # 1. Wikipedia Background
    wiki = investigate_company_wikipedia(company_name)
    wiki_summary = wiki.get("summary") if wiki.get("found") else None

    # 2. GitHub Projects & Tech Radar
    github_slug = company_name.lower().replace(" ", "").replace("-", "")
    projects = investigate_company_github_projects(github_slug)
    top_projects_json = json.dumps(projects) if projects else None

    # Tech Radar summary (extract primary languages & tags)
    tech_radar: dict[str, Any] = {
        "languages": list({p["language"] for p in projects if p.get("language")}),
        "active_repos_count": len(projects),
        "stars_total": sum(p.get("stars", 0) for p in projects),
    }
    tech_radar_json = json.dumps(tech_radar) if projects else None
    github_org_url = f"https://github.com/{github_slug}" if projects else None

    # 3. Persist to career_watchlist
    try:
        conn.execute(
            """
            UPDATE career_watchlist
            SET wikipedia_summary = COALESCE(?, wikipedia_summary),
                github_org_url = COALESCE(?, github_org_url),
                top_projects_json = COALESCE(?, top_projects_json),
                tech_radar_json = COALESCE(?, tech_radar_json),
                investigated_at = ?
            WHERE LOWER(company_name) = LOWER(?) OR LOWER(slug) = LOWER(?)
            """,
            (wiki_summary, github_org_url, top_projects_json, tech_radar_json, now, company_name, company_name),
        )
        if hasattr(conn, "commit"):
            conn.commit()
    except Exception as e:
        logger.warning("Failed saving investigation for %s: %s", company_name, e)

    return {
        "company_name": company_name,
        "investigated_at": now,
        "wikipedia": wiki,
        "github_org_url": github_org_url,
        "projects": projects,
        "tech_radar": tech_radar,
    }


