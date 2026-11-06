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

    # Deduplicate
    results["corporate_emails"] = list(dict.fromkeys(results["corporate_emails"]))
    results["personal_emails"] = list(dict.fromkeys(results["personal_emails"]))

    return results
