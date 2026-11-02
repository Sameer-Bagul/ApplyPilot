"""Direct public ATS JSON board pollers.

Fetches structured job openings directly from official public APIs for Greenhouse,
Lever, and Ashby boards without web scraping or headless browser execution.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

_USER_AGENT = "ApplyPilot/1.0 (Direct Career Feeds; contact@applypilot.local)"


def poll_greenhouse_board(board_token: str, timeout: float = 10.0) -> list[dict[str, Any]]:
    """Fetch active jobs from public Greenhouse Job Board API.

    URL: https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
    """
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            jobs = data.get("jobs", [])
            normalized = []
            for j in jobs:
                normalized.append({
                    "title": j.get("title", ""),
                    "url": j.get("absolute_url", ""),
                    "company": board_token,
                    "location": j.get("location", {}).get("name", "Remote"),
                    "description": j.get("content", ""),
                    "ats_provider": "greenhouse",
                    "execution_route": "PORTAL_ONLY",
                    "site": "greenhouse",
                })
            return normalized
    except Exception as e:
        logger.warning("Failed to poll Greenhouse board '%s': %s", board_token, e)
        return []


def poll_lever_board(board_token: str, timeout: float = 10.0) -> list[dict[str, Any]]:
    """Fetch active jobs from public Lever Postings API.

    URL: https://api.lever.co/v0/postings/{board_token}?mode=json
    """
    url = f"https://api.lever.co/v0/postings/{board_token}?mode=json"
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            postings = json.loads(resp.read().decode("utf-8"))
            normalized = []
            for p in postings:
                categories = p.get("categories", {})
                location = categories.get("location", "Remote")
                normalized.append({
                    "title": p.get("text", ""),
                    "url": p.get("hostedUrl", ""),
                    "company": board_token,
                    "location": location,
                    "description": p.get("descriptionPlain", "") or p.get("description", ""),
                    "ats_provider": "lever",
                    "execution_route": "PORTAL_ONLY",
                    "site": "lever",
                })
            return normalized
    except Exception as e:
        logger.warning("Failed to poll Lever board '%s': %s", board_token, e)
        return []


def poll_ashby_board(board_token: str, timeout: float = 10.0) -> list[dict[str, Any]]:
    """Fetch active jobs from public Ashby Job Board API.

    URL: https://api.ashbyhq.com/posting-api/job-board/{board_token}
    """
    url = f"https://api.ashbyhq.com/posting-api/job-board/{board_token}"
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            postings = data.get("jobs", [])
            normalized = []
            for p in postings:
                normalized.append({
                    "title": p.get("title", ""),
                    "url": p.get("jobUrl", ""),
                    "company": board_token,
                    "location": p.get("location", "Remote"),
                    "description": p.get("descriptionHtml", ""),
                    "ats_provider": "ashby",
                    "execution_route": "PORTAL_ONLY",
                    "site": "ashby",
                })
            return normalized
    except Exception as e:
        logger.warning("Failed to poll Ashby board '%s': %s", board_token, e)
        return []


def poll_board(ats_provider: str, board_token: str) -> list[dict[str, Any]]:
    """Poll jobs for a given ATS provider and board token."""
    provider = ats_provider.lower().strip()
    if provider == "greenhouse":
        return poll_greenhouse_board(board_token)
    elif provider == "lever":
        return poll_lever_board(board_token)
    elif provider == "ashby":
        return poll_ashby_board(board_token)
    else:
        logger.warning("Unsupported direct ATS provider: %s", ats_provider)
        return []


def poll_watchlist(watchlist_entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Poll all configured companies in the career watchlist."""
    all_jobs: list[dict[str, Any]] = []
    for entry in watchlist_entries:
        provider = entry.get("ats_provider")
        token = entry.get("ats_board_token")
        if provider and token:
            jobs = poll_board(provider, token)
            # Annotate official company name if provided
            cname = entry.get("company_name")
            if cname:
                for j in jobs:
                    j["company"] = cname
            all_jobs.extend(jobs)
    return all_jobs
