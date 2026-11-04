"""FreeHire Harvester for ApplyPilot.

Connects to FreeHire (4.7M+ IT jobs catalogue straight from company ATS boards)
via its official MCP JSON-RPC endpoint and keyless REST API.
Enables deep domain looping across engineering categories, seniorities, and regions.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any, Generator

from applypilot.database import get_connection, init_db, write_with_retry
from applypilot.discovery.lead_extractor import classify_execution_route

logger = logging.getLogger(__name__)

FREEHIRE_MCP_URL = "https://freehire.me/api/v1/mcp"
FREEHIRE_REST_URL = "https://freehire.me/api/v1"

# Curated engineering domains in FreeHire catalogue
FREEHIRE_TECH_CATEGORIES = [
    "ai_engineering",
    "ml_ai",
    "software_engineering",
    "fullstack",
    "backend",
    "frontend",
    "devops",
    "sre",
    "data_engineering",
    "data_science",
    "data_analytics",
    "solutions_engineering",
    "architecture",
    "security",
    "mobile",
    "qa",
]

FREEHIRE_SENIORITIES = ["senior", "lead", "staff", "principal", "middle"]
FREEHIRE_WORK_MODES = ["remote", "hybrid", "onsite"]
FREEHIRE_REGIONS = ["global", "north_america", "eu", "apac", "uk"]


class FreeHireClient:
    """Client for querying the FreeHire MCP & REST service."""

    def __init__(self, mcp_url: str = FREEHIRE_MCP_URL, timeout: float = 30.0):
        self.mcp_url = mcp_url
        self.timeout = timeout
        self._request_id = 1

    def call_mcp_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool call against FreeHire's MCP JSON-RPC endpoint."""
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        req = urllib.request.Request(
            self.mcp_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream, application/json",
                "User-Agent": "ApplyPilot/2.0",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw_bytes = resp.read()
                raw_text = raw_bytes.decode("utf-8")
        except urllib.error.HTTPError as e:
            logger.warning("FreeHire MCP HTTP error %s: %s", e.code, e.reason)
            return {"error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            logger.warning("FreeHire MCP request failed: %s", e)
            return {"error": str(e)}

        # FreeHire sends SSE stream or direct JSON
        lines = raw_text.splitlines()
        for line in lines:
            line_str = line.strip()
            if line_str.startswith("data: "):
                json_str = line_str[6:].strip()
                try:
                    data = json.loads(json_str)
                    result = data.get("result", {})
                    # Result typically has structuredContent or content array
                    if "structuredContent" in result:
                        return result["structuredContent"]
                    if "content" in result and isinstance(result["content"], list):
                        for item in result["content"]:
                            if item.get("type") == "text":
                                try:
                                    return json.loads(item.get("text", "{}"))
                                except Exception:
                                    pass
                    return result
                except Exception as parse_err:
                    logger.debug("Failed to parse SSE JSON chunk: %s", parse_err)

        try:
            data = json.loads(raw_text)
            return data.get("result", data)
        except Exception:
            return {"error": "unparseable_response", "raw": raw_text[:500]}

    def search_jobs(
        self,
        category: list[str] | str | None = None,
        query: str | None = None,
        work_mode: list[str] | str | None = None,
        seniority: list[str] | str | None = None,
        skills: list[str] | None = None,
        countries: list[str] | None = None,
        regions: list[str] | None = None,
        sources: list[str] | None = None,
        limit: int = 25,
        offset: int = 0,
        posted_within_days: int = 14,
    ) -> dict[str, Any]:
        """Search FreeHire's IT jobs catalogue with rich faceted filters."""
        args: dict[str, Any] = {"limit": limit, "offset": offset}

        if category:
            args["category"] = [category] if isinstance(category, str) else category
        if query:
            args["query"] = query
        if work_mode:
            args["work_mode"] = [work_mode] if isinstance(work_mode, str) else work_mode
        if seniority:
            args["seniority"] = [seniority] if isinstance(seniority, str) else seniority
        if skills:
            args["skills"] = skills
        if countries:
            args["countries"] = countries
        if regions:
            args["regions"] = regions
        if sources:
            args["sources"] = [sources] if isinstance(sources, str) else sources
        if posted_within_days:
            args["posted_within_days"] = posted_within_days

        return self.call_mcp_tool("search_jobs", args)

    def get_job(self, slug: str) -> dict[str, Any]:
        """Retrieve full job details including description and ATS handling."""
        return self.call_mcp_tool("get_job", {"slug": slug})

    def check_jobs_open(self, slugs: list[str]) -> dict[str, Any]:
        """Batch-check whether postings are still active (up to 50 slugs)."""
        return self.call_mcp_tool("check_jobs_open", {"slugs": slugs[:50]})

    def get_company(self, slug: str) -> dict[str, Any]:
        """Retrieve employer metadata and number of active postings."""
        return self.call_mcp_tool("get_company", {"slug": slug})


def format_salary(min_amt: Any, max_amt: Any, currency: str = "USD", period: str = "year") -> str | None:
    """Format salary range string."""
    if not min_amt and not max_amt:
        return None
    curr = currency or "USD"
    p = f"/{period}" if period else ""
    try:
        if min_amt and max_amt:
            return f"{curr} {int(min_amt):,} - {int(max_amt):,}{p}"
        elif min_amt:
            return f"{curr} {int(min_amt):,}{p}"
        elif max_amt:
            return f"{curr} up to {int(max_amt):,}{p}"
    except (ValueError, TypeError):
        return None
    return None


def ingest_freehire_jobs(
    jobs_data: list[dict[str, Any]],
    conn: sqlite3.Connection | None = None,
    fetch_full_details: bool = False,
    client: FreeHireClient | None = None,
) -> dict[str, int]:
    """Store FreeHire postings in ApplyPilot jobs table with deduplication.

    Returns stats dict: {"total": N, "new": N, "existing": N, "companies_added": N}
    """
    if conn is None:
        conn = get_connection()
    if client is None and fetch_full_details:
        client = FreeHireClient()

    now = datetime.now(timezone.utc).isoformat()
    stats = {"total": len(jobs_data), "new": 0, "existing": 0, "companies_added": 0}

    def _do_inserts() -> None:
        for job in jobs_data:
            # Primary URL preference: employer's direct posting, then FreeHire URL
            official_url = job.get("official_job_url")
            fh_url = job.get("url") or f"https://freehire.me/jobs/{job.get('slug')}"
            primary_url = official_url or fh_url
            slug = job.get("slug", "")

            if not primary_url:
                continue

            title = job.get("title", "Software Engineer")
            company = job.get("company", "Tech Company")
            company_slug = job.get("company_slug")
            location = job.get("location") or "Remote"
            summary = job.get("summary") or ""
            source = job.get("source") or "freehire"
            site_label = f"freehire/{source}"
            strategy = "freehire"
            posted_at = job.get("posted_at")

            # Format salary
            salary_str = format_salary(
                job.get("salary_min"),
                job.get("salary_max"),
                job.get("salary_currency", "USD"),
                job.get("salary_period", "year"),
            )

            # Execution route classification
            route = "PORTAL_ONLY"
            if official_url:
                route = classify_execution_route(has_email=False, has_portal_url=True)

            # Optionally fetch full description for high-priority jobs
            full_desc = None
            if fetch_full_details and slug and client:
                try:
                    full_info = client.get_job(slug)
                    full_desc = full_info.get("description") or full_info.get("text")
                except Exception as e:
                    logger.debug("Failed to fetch full detail for %s: %s", slug, e)

            # If no full description fetched yet, summary can serve as preliminary description
            description_to_store = full_desc or summary
            has_sufficient_desc = bool(description_to_store and len(description_to_store) >= 200)
            initial_state = "enriched" if has_sufficient_desc else "discovered"
            detail_scraped_at = now if has_sufficient_desc else None

            # Check if job already exists in DB
            existing_row = conn.execute("SELECT 1 FROM jobs WHERE url = ?", (primary_url,)).fetchone()

            if existing_row:
                stats["existing"] += 1
                try:
                    conn.execute(
                        """
                        UPDATE jobs SET
                            discovered_at = COALESCE(discovered_at, ?),
                            application_url = COALESCE(application_url, ?),
                            salary = COALESCE(salary, ?),
                            full_description = COALESCE(full_description, ?),
                            detail_scraped_at = COALESCE(detail_scraped_at, ?),
                            execution_route = COALESCE(?, execution_route)
                        WHERE url = ?
                        """,
                        (
                            now,
                            official_url or primary_url,
                            salary_str,
                            description_to_store if has_sufficient_desc else None,
                            detail_scraped_at,
                            route,
                            primary_url,
                        ),
                    )
                except Exception as update_err:
                    logger.debug("FreeHire job update notice: %s", update_err)
                continue

            try:
                conn.execute(
                    """
                    INSERT INTO jobs (
                        url, title, company, salary, description, location, site, strategy,
                        discovered_at, full_description, application_url, detail_scraped_at,
                        posted_at, execution_route, state
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        primary_url,
                        title,
                        company,
                        salary_str,
                        summary[:1000] if summary else "",
                        location,
                        site_label,
                        strategy,
                        now,
                        description_to_store if has_sufficient_desc else None,
                        official_url or primary_url,
                        detail_scraped_at,
                        posted_at,
                        route,
                        initial_state,
                    ),
                )

                # Record transition
                conn.execute(
                    """
                    INSERT INTO job_state_transitions (job_url, from_state, to_state, at, reason, metadata)
                    VALUES (?, NULL, ?, ?, ?, ?)
                    """,
                    (primary_url, initial_state, now, f"discovered via {site_label}", None),
                )
                stats["new"] += 1

                # Upsert into career_watchlist so ApplyPilot looper can extract HR leads & monitor ATS changes
                if company and len(company.strip()) > 1:
                    try:
                        from applypilot.database import upsert_career_watchlist
                        upsert_career_watchlist(
                            company_name=company.strip(),
                            priority_tier=2,
                            is_vip=0,
                            conn=conn,
                        )
                        stats["companies_added"] += 1
                    except Exception:
                        pass

            except sqlite3.IntegrityError:
                stats["existing"] += 1
            except Exception as e:
                logger.debug("FreeHire job insert notice: %s", e)

    write_with_retry(conn, _do_inserts)
    return stats


def harvest_freehire_domain(
    category: str | None = None,
    work_modes: list[str] | None = None,
    seniorities: list[str] | None = None,
    regions: list[str] | None = None,
    sources: list[str] | None = None,
    limit: int = 50,
    posted_within_days: int = 14,
    conn: sqlite3.Connection | None = None,
    client: FreeHireClient | None = None,
) -> dict[str, Any]:
    """Harvest one domain / role family or specific source from FreeHire catalogue."""
    if client is None:
        client = FreeHireClient()
    if conn is None:
        conn = get_connection()

    label = f"domain '{category}'" if category else f"sources '{sources}'"
    logger.info("Harvesting FreeHire %s (limit=%d)...", label, limit)
    res = client.search_jobs(
        category=category,
        work_mode=work_modes or ["remote", "hybrid"],
        seniority=seniorities or ["senior", "lead", "staff", "principal", "middle"],
        regions=regions or ["global", "north_america", "eu", "apac"],
        sources=sources,
        limit=limit,
        posted_within_days=posted_within_days,
    )

    jobs = res.get("jobs", [])
    total_in_catalogue = res.get("total", len(jobs))

    ingest_stats = ingest_freehire_jobs(jobs, conn=conn, client=client)
    return {
        "category": category,
        "catalogue_total": total_in_catalogue,
        "scraped": len(jobs),
        "ingested_new": ingest_stats.get("new", 0),
        "existing": ingest_stats.get("existing", 0),
        "companies_added": ingest_stats.get("companies_added", 0),
    }


def loop_all_freehire_domains(
    categories: list[str] | None = None,
    limit_per_category: int = 30,
    posted_within_days: int = 14,
    delay_between_domains: float = 1.0,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Iterate across all tech categories and ingest massive batches of live vacancies."""
    if conn is None:
        conn = get_connection()

    client = FreeHireClient()
    active_categories = categories or list(FREEHIRE_TECH_CATEGORIES)

    total_scraped = 0
    total_new = 0
    total_existing = 0
    total_companies = 0
    domain_reports: list[dict[str, Any]] = []

    for idx, cat in enumerate(active_categories, start=1):
        try:
            report = harvest_freehire_domain(
                category=cat,
                limit=limit_per_category,
                posted_within_days=posted_within_days,
                conn=conn,
                client=client,
            )
            total_scraped += report.get("scraped", 0)
            total_new += report.get("ingested_new", 0)
            total_existing += report.get("existing", 0)
            total_companies += report.get("companies_added", 0)
            domain_reports.append(report)

            logger.info(
                "[%d/%d] FreeHire '%s': %d scraped -> %d new, %d existing",
                idx,
                len(active_categories),
                cat,
                report.get("scraped", 0),
                report.get("ingested_new", 0),
                report.get("existing", 0),
            )
        except Exception as e:
            logger.warning("Error harvesting domain '%s': %s", cat, e)
            domain_reports.append({"category": cat, "error": str(e)})

        if idx < len(active_categories) and delay_between_domains > 0:
            time.sleep(delay_between_domains)

    return {
        "total_domains_scanned": len(active_categories),
        "total_jobs_scraped": total_scraped,
        "total_new_jobs": total_new,
        "total_existing_jobs": total_existing,
        "total_companies_watchlist_added": total_companies,
        "domains": domain_reports,
    }
