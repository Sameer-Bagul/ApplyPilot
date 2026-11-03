"""Direct public ATS JSON board pollers (11 ATS Platforms).

Fetches structured job openings directly from official public APIs for:
1. Greenhouse (boards-api.greenhouse.io)
2. Lever (api.lever.co)
3. Ashby REST & GraphQL (api.ashbyhq.com / jobs.ashbyhq.com)
4. Workday ({host}/wday/cxs/{tenant}/{site}/jobs)
5. Workable (apply.workable.com/api/v1/widget/accounts/{slug})
6. SmartRecruiters (api.smartrecruiters.com/v1/companies/{slug}/postings)
7. BambooHR ({slug}.bamboohr.com/careers/list)
8. Recruitee ({slug}.recruitee.com/api/offers/)
9. Teamtailor ({slug}.teamtailor.com/jobs.json)
10. Breezy HR ({slug}.breezy.hr/json)
11. Personio ({slug}.jobs.personio.de/xml)

Features:
- Fast, non-blocking HTTP requests with follow_redirects=False (302/307 skipped instantly)
- Normalized job output schemas with execution_route and ats_provider tags
"""

from __future__ import annotations

import json
import logging
import re
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_HEADERS = {
    "User-Agent": "ApplyPilot/1.0 (Direct Career Feeds; contact@applypilot.local)",
    "Accept": "application/json, */*",
}


def _get_client(timeout: float = 10.0) -> httpx.Client:
    """Create an HTTP client that does NOT follow redirects to quickly discard 302/307 home redirects."""
    return httpx.Client(headers=_DEFAULT_HEADERS, follow_redirects=False, timeout=timeout)


# 1. Greenhouse
def poll_greenhouse_board(board_token: str, client: httpx.Client | None = None, timeout: float = 10.0) -> list[dict[str, Any]]:
    """Fetch active jobs from public Greenhouse Job Board API."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
    should_close = False
    if client is None:
        client = _get_client(timeout)
        should_close = True

    try:
        resp = client.get(url)
        if resp.status_code != 200:
            return []
        data = resp.json()
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
        logger.debug("Failed to poll Greenhouse board '%s': %s", board_token, e)
        return []
    finally:
        if should_close:
            client.close()


# 2. Lever
def poll_lever_board(board_token: str, client: httpx.Client | None = None, timeout: float = 10.0) -> list[dict[str, Any]]:
    """Fetch active jobs from public Lever Postings API."""
    url = f"https://api.lever.co/v0/postings/{board_token}?mode=json"
    should_close = False
    if client is None:
        client = _get_client(timeout)
        should_close = True

    try:
        resp = client.get(url)
        if resp.status_code != 200:
            return []
        postings = resp.json()
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
        logger.debug("Failed to poll Lever board '%s': %s", board_token, e)
        return []
    finally:
        if should_close:
            client.close()


# 3. Ashby (REST & GraphQL)
def poll_ashby_board(board_token: str, client: httpx.Client | None = None, timeout: float = 10.0) -> list[dict[str, Any]]:
    """Fetch active jobs from public Ashby Job Board API."""
    url = f"https://api.ashbyhq.com/posting-api/job-board/{board_token}"
    should_close = False
    if client is None:
        client = _get_client(timeout)
        should_close = True

    try:
        resp = client.get(url)
        if resp.status_code == 200:
            data = resp.json()
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

        # Fallback: Ashby GraphQL
        gql_url = "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams"
        gql_query = {
            "operationName": "ApiJobBoardWithTeams",
            "variables": {"organizationHostedJobsPageName": board_token},
            "query": "query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) { jobBoard: jobBoardWithTeams(organizationHostedJobsPageName: $organizationHostedJobsPageName) { jobPostings { id title locationName externalLink } } }"
        }
        resp = client.post(gql_url, json=gql_query)
        if resp.status_code == 200:
            data = resp.json()
            postings = data.get("data", {}).get("jobBoard", {}).get("jobPostings", [])
            normalized = []
            for p in postings:
                normalized.append({
                    "title": p.get("title", ""),
                    "url": p.get("externalLink") or f"https://jobs.ashbyhq.com/{board_token}/{p.get('id')}",
                    "company": board_token,
                    "location": p.get("locationName", "Remote"),
                    "description": "",
                    "ats_provider": "ashby",
                    "execution_route": "PORTAL_ONLY",
                    "site": "ashby",
                })
            return normalized
        return []
    except Exception as e:
        logger.debug("Failed to poll Ashby board '%s': %s", board_token, e)
        return []
    finally:
        if should_close:
            client.close()


# 4. Workday
def poll_workday_board(host: str, tenant: str, site: str = "External", client: httpx.Client | None = None, timeout: float = 12.0) -> list[dict[str, Any]]:
    """Fetch active jobs from Workday CXS JSON API."""
    url = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
    should_close = False
    if client is None:
        client = _get_client(timeout)
        should_close = True

    try:
        payload = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}
        resp = client.post(url, json=payload)
        if resp.status_code != 200:
            return []
        data = resp.json()
        job_postings = data.get("jobPostings", [])
        normalized = []
        for j in job_postings:
            path = j.get("externalPath", "")
            full_url = f"https://{host}/en-US/{tenant}{path}" if path else f"https://{host}"
            normalized.append({
                "title": j.get("title", ""),
                "url": full_url,
                "company": tenant,
                "location": j.get("locationsText", "Remote"),
                "description": "",
                "ats_provider": "workday",
                "execution_route": "PORTAL_ONLY",
                "site": "workday",
            })
        return normalized
    except Exception as e:
        logger.debug("Failed to poll Workday board for %s: %s", tenant, e)
        return []
    finally:
        if should_close:
            client.close()


# 5. Workable
def poll_workable_board(board_token: str, client: httpx.Client | None = None, timeout: float = 10.0) -> list[dict[str, Any]]:
    """Fetch active jobs from Workable widget JSON API."""
    url = f"https://apply.workable.com/api/v1/widget/accounts/{board_token}?details=true"
    should_close = False
    if client is None:
        client = _get_client(timeout)
        should_close = True

    try:
        resp = client.get(url)
        if resp.status_code != 200:
            return []
        data = resp.json()
        jobs = data.get("jobs", [])
        normalized = []
        for j in jobs:
            loc = j.get("city") or j.get("country") or "Remote"
            normalized.append({
                "title": j.get("title", ""),
                "url": j.get("url") or f"https://apply.workable.com/{board_token}/j/{j.get('shortcode')}/",
                "company": board_token,
                "location": loc,
                "description": j.get("description", ""),
                "ats_provider": "workable",
                "execution_route": "PORTAL_ONLY",
                "site": "workable",
            })
        return normalized
    except Exception as e:
        logger.debug("Failed to poll Workable board '%s': %s", board_token, e)
        return []
    finally:
        if should_close:
            client.close()


# 6. SmartRecruiters
def poll_smartrecruiters_board(board_token: str, client: httpx.Client | None = None, timeout: float = 10.0) -> list[dict[str, Any]]:
    """Fetch active jobs from SmartRecruiters public API."""
    url = f"https://api.smartrecruiters.com/v1/companies/{board_token}/postings"
    should_close = False
    if client is None:
        client = _get_client(timeout)
        should_close = True

    try:
        resp = client.get(url)
        if resp.status_code != 200:
            return []
        data = resp.json()
        postings = data.get("content", [])
        normalized = []
        for p in postings:
            location_info = p.get("location", {})
            loc_str = location_info.get("city") or location_info.get("country") or "Remote"
            normalized.append({
                "title": p.get("name", ""),
                "url": f"https://jobs.smartrecruiters.com/{board_token}/{p.get('id')}",
                "company": board_token,
                "location": loc_str,
                "description": "",
                "ats_provider": "smartrecruiters",
                "execution_route": "PORTAL_ONLY",
                "site": "smartrecruiters",
            })
        return normalized
    except Exception as e:
        logger.debug("Failed to poll SmartRecruiters board '%s': %s", board_token, e)
        return []
    finally:
        if should_close:
            client.close()


# 7. BambooHR
def poll_bamboohr_board(board_token: str, client: httpx.Client | None = None, timeout: float = 10.0) -> list[dict[str, Any]]:
    """Fetch active jobs from BambooHR careers list endpoint."""
    url = f"https://{board_token}.bamboohr.com/careers/list"
    should_close = False
    if client is None:
        client = _get_client(timeout)
        should_close = True

    try:
        resp = client.get(url, headers={"Accept": "application/json"})
        if resp.status_code != 200:
            return []
        data = resp.json()
        result = data.get("result", [])
        normalized = []
        for r in result:
            job_id = r.get("id")
            normalized.append({
                "title": r.get("jobOpeningName", ""),
                "url": f"https://{board_token}.bamboohr.com/careers/{job_id}" if job_id else url,
                "company": board_token,
                "location": r.get("location", {}).get("city", "Remote"),
                "description": "",
                "ats_provider": "bamboohr",
                "execution_route": "PORTAL_ONLY",
                "site": "bamboohr",
            })
        return normalized
    except Exception as e:
        logger.debug("Failed to poll BambooHR board '%s': %s", board_token, e)
        return []
    finally:
        if should_close:
            client.close()


# 8. Recruitee
def poll_recruitee_board(board_token: str, client: httpx.Client | None = None, timeout: float = 10.0) -> list[dict[str, Any]]:
    """Fetch active jobs from Recruitee offers API."""
    url = f"https://{board_token}.recruitee.com/api/offers/"
    should_close = False
    if client is None:
        client = _get_client(timeout)
        should_close = True

    try:
        resp = client.get(url)
        if resp.status_code != 200:
            return []
        data = resp.json()
        offers = data.get("offers", [])
        normalized = []
        for o in offers:
            normalized.append({
                "title": o.get("title", ""),
                "url": o.get("careers_url") or f"https://{board_token}.recruitee.com/o/{o.get('slug')}",
                "company": board_token,
                "location": o.get("city") or o.get("country") or "Remote",
                "description": o.get("description", ""),
                "ats_provider": "recruitee",
                "execution_route": "PORTAL_ONLY",
                "site": "recruitee",
            })
        return normalized
    except Exception as e:
        logger.debug("Failed to poll Recruitee board '%s': %s", board_token, e)
        return []
    finally:
        if should_close:
            client.close()


# 9. Teamtailor
def poll_teamtailor_board(board_token: str, client: httpx.Client | None = None, timeout: float = 10.0) -> list[dict[str, Any]]:
    """Fetch active jobs from Teamtailor JSON feed."""
    url = f"https://{board_token}.teamtailor.com/jobs.json"
    should_close = False
    if client is None:
        client = _get_client(timeout)
        should_close = True

    try:
        resp = client.get(url)
        if resp.status_code != 200:
            return []
        data = resp.json()
        jobs = data if isinstance(data, list) else data.get("data", [])
        normalized = []
        for j in jobs:
            attrs = j.get("attributes", j)
            normalized.append({
                "title": attrs.get("title", ""),
                "url": attrs.get("external_url") or attrs.get("url") or url,
                "company": board_token,
                "location": attrs.get("location", "Remote"),
                "description": attrs.get("body", ""),
                "ats_provider": "teamtailor",
                "execution_route": "PORTAL_ONLY",
                "site": "teamtailor",
            })
        return normalized
    except Exception as e:
        logger.debug("Failed to poll Teamtailor board '%s': %s", board_token, e)
        return []
    finally:
        if should_close:
            client.close()


# 10. Breezy HR
def poll_breezy_board(board_token: str, client: httpx.Client | None = None, timeout: float = 10.0) -> list[dict[str, Any]]:
    """Fetch active jobs from Breezy HR JSON endpoint."""
    url = f"https://{board_token}.breezy.hr/json"
    should_close = False
    if client is None:
        client = _get_client(timeout)
        should_close = True

    try:
        resp = client.get(url)
        if resp.status_code != 200:
            return []
        postings = resp.json()
        normalized = []
        for p in postings:
            normalized.append({
                "title": p.get("name", ""),
                "url": p.get("url") or f"https://{board_token}.breezy.hr/p/{p.get('id')}",
                "company": board_token,
                "location": p.get("location", {}).get("name", "Remote") if isinstance(p.get("location"), dict) else "Remote",
                "description": "",
                "ats_provider": "breezy",
                "execution_route": "PORTAL_ONLY",
                "site": "breezy",
            })
        return normalized
    except Exception as e:
        logger.debug("Failed to poll Breezy board '%s': %s", board_token, e)
        return []
    finally:
        if should_close:
            client.close()


# 11. Personio (XML)
def poll_personio_board(board_token: str, client: httpx.Client | None = None, timeout: float = 10.0) -> list[dict[str, Any]]:
    """Fetch active jobs from Personio XML feed."""
    url = f"https://{board_token}.jobs.personio.de/xml"
    should_close = False
    if client is None:
        client = _get_client(timeout)
        should_close = True

    try:
        resp = client.get(url)
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.content)
        normalized = []
        for pos in root.findall(".//position"):
            name = pos.findtext("name", "")
            pos_id = pos.findtext("id", "")
            office = pos.findtext("office", "Remote")
            normalized.append({
                "title": name,
                "url": f"https://{board_token}.jobs.personio.de/job/{pos_id}",
                "company": board_token,
                "location": office,
                "description": "",
                "ats_provider": "personio",
                "execution_route": "PORTAL_ONLY",
                "site": "personio",
            })
        return normalized
    except Exception as e:
        logger.debug("Failed to poll Personio board '%s': %s", board_token, e)
        return []
    finally:
        if should_close:
            client.close()


# Master Dispatcher
def poll_board(ats_provider: str, board_token: str, client: httpx.Client | None = None) -> list[dict[str, Any]]:
    """Poll jobs for any of the 11 supported ATS platforms."""
    provider = ats_provider.lower().strip()
    if provider == "greenhouse":
        return poll_greenhouse_board(board_token, client)
    elif provider == "lever":
        return poll_lever_board(board_token, client)
    elif provider == "ashby":
        return poll_ashby_board(board_token, client)
    elif provider == "workable":
        return poll_workable_board(board_token, client)
    elif provider == "smartrecruiters":
        return poll_smartrecruiters_board(board_token, client)
    elif provider == "bamboohr":
        return poll_bamboohr_board(board_token, client)
    elif provider == "recruitee":
        return poll_recruitee_board(board_token, client)
    elif provider == "teamtailor":
        return poll_teamtailor_board(board_token, client)
    elif provider == "breezy":
        return poll_breezy_board(board_token, client)
    elif provider == "personio":
        return poll_personio_board(board_token, client)
    elif provider == "workday":
        # token is expected as "host/tenant/site" or "host/tenant"
        parts = board_token.split("/")
        if len(parts) >= 2:
            host, tenant = parts[0], parts[1]
            site = parts[2] if len(parts) > 2 else "External"
            return poll_workday_board(host, tenant, site, client)
    return []


def poll_watchlist(watchlist_entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Poll all configured companies in the career watchlist."""
    all_jobs: list[dict[str, Any]] = []
    with _get_client() as client:
        for entry in watchlist_entries:
            provider = entry.get("ats_provider")
            token = entry.get("ats_board_token")
            if provider and token:
                jobs = poll_board(provider, token, client=client)
                cname = entry.get("company_name")
                if cname:
                    for j in jobs:
                        j["company"] = cname
                all_jobs.extend(jobs)
    return all_jobs
