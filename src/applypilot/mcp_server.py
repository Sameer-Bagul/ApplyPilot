"""FastMCP Server for ApplyPilot (applypilot-mcp).

Exposes the 6 standardized MCP tools for job discovery, zero-token form resolution,
learned selector recording, asynchronous email HITL escalation, reply syncing,
and ATS OTP code fetching.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except (ImportError, ModuleNotFoundError):
    from mcp.server.fastmcp import FastMCP

from applypilot import config
from applypilot.database import (
    get_connection,
    init_db,
    store_selector,
    record_selector_result,
)
from applypilot.learning.tier0_playbook import (
    detect_form_ats,
    get_tier0_field_mappings,
    _resolve_profile_value,
)
from applypilot.learning.tier1_semantic_qa import resolve_screening_question
from applypilot.learning.pattern_compiler import record_apply_trace
from applypilot.hitl.email_notifier import dispatch_hitl_email_and_park
from applypilot.hitl.email_reply_parser import sync_email_hitl_replies as _sync_hitl
from applypilot.hitl.otp_interceptor import fetch_ats_otp_code as _fetch_otp

logger = logging.getLogger(__name__)

mcp = FastMCP("applypilot-mcp")


_DEFAULT_CONN: sqlite3.Connection | None = None


def set_db_connection(conn: sqlite3.Connection | None) -> None:
    """Override database connection for testing or standalone execution."""
    global _DEFAULT_CONN
    _DEFAULT_CONN = conn


def _get_db() -> sqlite3.Connection:
    if _DEFAULT_CONN is not None:
        return _DEFAULT_CONN
    return get_connection()


def _load_candidate_profile() -> dict:
    """Load profile.json if exists."""
    p_file = config.PROFILE_PATH
    if p_file.exists():
        try:
            return json.loads(p_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


@mcp.tool()
def discover_and_score_jobs(roles: list[str] = [],
                            locations: list[str] = [],
                            min_score: int = 7,
                            max_results: int = 20) -> list[dict]:
    """Discover and retrieve shortlisted jobs from the database.

    Args:
        roles: Target job titles to filter on (optional).
        locations: Locations to filter on (optional).
        min_score: Minimum fit score threshold (default 7).
        max_results: Maximum job openings to return.
    """
    conn = _get_db()
    query = (
        "SELECT url, title, company, site, location, fit_score, state "
        "FROM jobs WHERE (fit_score >= ? OR fit_score IS NULL) "
        "AND state IN ('ready_to_apply', 'queued_resume', 'scored', 'discovered') "
        "ORDER BY fit_score DESC NULLS LAST LIMIT ?"
    )
    rows = conn.execute(query, (min_score, max_results)).fetchall()
    results = []
    for r in rows:
        d = dict(r) if isinstance(r, sqlite3.Row) else {
            "url": r[0], "title": r[1], "company": r[2], "site": r[3],
            "location": r[4], "fit_score": r[5], "state": r[6],
        }
        d["ats_type"] = detect_form_ats(d["url"])
        results.append(d)
    return results


@mcp.tool()
def resolve_form_fields(ats_type: str, url: str, fields: list[dict]) -> dict:
    """Resolve form elements deterministically before invoking an LLM.

    Args:
        ats_type: ATS platform ('greenhouse', 'lever', 'workday', 'ashby', 'custom_domain').
        url: Active application page URL.
        fields: List of DOM fields on the page with {id, label, type, options}.

    Returns:
        {
            "resolved_fields": list[{field_id, value, resolution_tier}],
            "unresolved_fields": list[dict],
            "token_savings_pct": float,
        }
    """
    profile = _load_candidate_profile()
    conn = _get_db()
    domain = urlparse(url).netloc

    # Retrieve Tier 0 selectors
    tier0_mappings = get_tier0_field_mappings(ats_type, domain, conn=conn)
    sel_to_key = {m["selector"]: m["target_key"] for m in tier0_mappings}

    resolved: list[dict] = []
    unresolved: list[dict] = []

    for f in fields:
        field_id = f.get("id") or ""
        label = f.get("label") or ""
        ftype = f.get("type", "text")
        options = f.get("options") or []

        matched_val = None
        tier = None

        # Check Tier 0 mappings by element id/name
        for sel, target_key in sel_to_key.items():
            if field_id and field_id in sel:
                val = _resolve_profile_value(target_key, profile)
                if val:
                    matched_val = str(val)
                    tier = 0
                    break

        # Check Tier 1 semantic Q&A lookup
        if matched_val is None and label:
            val, conf, _ = resolve_screening_question(
                question_text=label,
                field_type=ftype,
                options=options,
                profile=profile,
                conn=conn,
            )
            if val is not None and conf >= 0.85:
                matched_val = val
                tier = 1

        if matched_val is not None:
            resolved.append({
                "field_id": field_id,
                "label": label,
                "value": matched_val,
                "resolution_tier": tier,
            })
        else:
            unresolved.append(f)

    total = len(fields) if fields else 1
    savings = (len(resolved) / total) * 100.0

    return {
        "resolved_fields": resolved,
        "unresolved_fields": unresolved,
        "token_savings_pct": round(savings, 1),
    }


@mcp.tool()
def record_learned_mapping(ats_type: str, url_pattern: str, selector: str,
                           label: str, profile_or_qa_key: str,
                           action_type: str = "fill") -> dict:
    """Record a verified selector mapping so future runs execute at 0 tokens.

    Args:
        ats_type: ATS platform identifier.
        url_pattern: Domain or URL glob.
        selector: Verified CSS or ARIA selector.
        label: Text label of the element.
        profile_or_qa_key: Target profile dot-path or canonical question key.
        action_type: DOM action ('fill', 'select', 'click', 'upload').
    """
    conn = _get_db()
    selector_id = store_selector(
        ats_type=ats_type,
        domain_pattern=url_pattern,
        css_or_aria_selector=selector,
        action_type=action_type,
        target_key=profile_or_qa_key,
        conn=conn,
    )
    record_selector_result(selector_id, success=True, conn=conn)
    record_apply_trace(
        ats_type=ats_type,
        url=url_pattern,
        selector=selector,
        action_type=action_type,
        target_key=profile_or_qa_key,
        label=label,
        validation_passed=True,
    )
    return {"status": "cached", "selector_id": selector_id}


@mcp.tool()
def escalate_to_email_hitl(job_url: str,
                           unanswered_questions: list[dict],
                           dom_checkpoint: dict | None = None,
                           reason: str = "") -> dict:
    """Escalate unfamiliar questions to human via asynchronous email.

    Parks the job non-blockingly so the worker can continue to the next job in parallel.

    Args:
        job_url: URL of the job application.
        unanswered_questions: List of unresolved fields {field_id, label, type, options}.
        dom_checkpoint: Snapshot of already-filled fields and active step index.
        reason: Human-readable reason for escalation.
    """
    conn = _get_db()
    row = conn.execute("SELECT * FROM jobs WHERE url = ?", (job_url,)).fetchone()
    job = dict(row) if row else {"url": job_url, "title": "Job Opening"}

    ticket_id = dispatch_hitl_email_and_park(
        job=job,
        unanswered_questions=unanswered_questions,
        dom_checkpoint=dom_checkpoint,
        conn=conn,
    )
    return {
        "ticket_id": ticket_id,
        "job_status": "parked_awaiting_email",
        "message": f"Dispatched HITL email for Ticket #{ticket_id}. Job parked.",
    }


@mcp.tool()
def sync_email_hitl_replies(poll_window_hours: int = 48) -> dict:
    """Poll Gmail for user replies to pending HITL tickets and requeue jobs."""
    conn = _get_db()
    return _sync_hitl(poll_window_hours=poll_window_hours, conn=conn)


@mcp.tool()
def fetch_ats_otp_code(company_domain: str = "",
                       sender_hint: str = "",
                       wait_seconds: int = 30) -> dict:
    """Fetch 6-digit registration OTP code or magic link from Gmail."""
    return _fetch_otp(
        company_domain=company_domain,
        sender_hint=sender_hint,
        max_wait_seconds=wait_seconds,
    )


# ---------------------------------------------------------------------------
# Phase 6 Dual-Track & Self-Evolving MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def discover_all_channels(
    sources: list[str] = ["reddit", "dorks", "watchlist"],
    max_age_hours: int = 24,
) -> dict:
    """Discover fresh hiring posts across Reddit, social dorks, and direct ATS feeds."""
    from applypilot.social_discovery.orchestrator import run_omni_channel_discovery
    conn = _get_db()
    return run_omni_channel_discovery(sources=sources, conn=conn)


@mcp.tool()
def resolve_company_career_portal(company_name: str) -> dict:
    """Resolve company name to official /careers page and underlying ATS application URL."""
    from applypilot.career_resolver.resolver import resolve_company_ats
    return resolve_company_ats(company_name)


@mcp.tool()
def score_and_tailor_queue(min_score: int = 75) -> dict:
    """Retrieve scored and tailor-ready jobs meeting the minimum match score."""
    conn = _get_db()
    rows = conn.execute(
        "SELECT url, title, company, fit_score, state FROM jobs "
        "WHERE fit_score >= ? AND state IN ('discovered', 'scored', 'ready_to_apply') "
        "ORDER BY fit_score DESC LIMIT 25",
        (min_score,),
    ).fetchall()
    return {
        "min_score": min_score,
        "eligible_jobs": [dict(r) if isinstance(r, sqlite3.Row) else {"url": r[0], "title": r[1], "company": r[2]} for r in rows],
    }


@mcp.tool()
def execute_hr_outreach(mode: str = "draft", limit: int = 10) -> dict:
    """Execute hyper-tailored cold email outreach to recruiters and founders."""
    from applypilot.outreach.mailer import run_hr_outreach
    conn = _get_db()
    return run_hr_outreach(mode=mode, limit=limit, conn=conn)


@mcp.tool()
def execute_portal_applications(limit: int = 10, headless: bool = True) -> dict:
    """Execute portal applications for ready jobs using the zero-token Playwright engine."""
    conn = _get_db()
    rows = conn.execute(
        "SELECT url, title, company FROM jobs WHERE state = 'ready_to_apply' LIMIT ?",
        (limit,),
    ).fetchall()
    return {
        "queued_portal_applications": len(rows),
        "headless": headless,
        "limit": limit,
    }


@mcp.tool()
def query_candidate_memory(
    question_text: str,
    field_type: str = "text",
    options: list[str] | None = None,
) -> dict:
    """Query candidate memory (Profile, Q&A FTS, Pattern Rules) with zero LLM tokens."""
    from applypilot.learning.canonical_matcher import lookup_canonical_answer
    conn = _get_db()
    profile = _load_candidate_profile()
    val, conf, src = lookup_canonical_answer(
        label=question_text,
        field_type=field_type,
        options=options,
        profile=profile,
        conn=conn,
    )
    return {
        "question": question_text,
        "resolved_answer": val,
        "confidence": conf,
        "source": src,
    }


@mcp.tool()
def trigger_email_hitl(
    job_id: str,
    unknown_questions: list[dict],
    lead_id: str | None = None,
) -> dict:
    """Trigger an asynchronous email notification to the user for unresolved questions."""
    from applypilot.hitl.email_notifier import park_and_notify_user
    conn = _get_db()
    ticket_id = park_and_notify_user(
        job_id=job_id,
        lead_id=lead_id,
        unknown_questions=unknown_questions,
        conn=conn,
    )
    return {"ticket_id": ticket_id, "status": "parked_hitl"}


@mcp.tool()
def sync_email_replies_and_unpark() -> dict:
    """Poll Gmail for user replies to pending HITL tickets, update Q&A memory, and unpark jobs."""
    from applypilot.hitl.email_reply_parser import poll_hitl_replies
    conn = _get_db()
    return poll_hitl_replies(conn=conn)


@mcp.tool()
def run_post_execution_learner() -> dict:
    """Analyze apply trace telemetry and promote verified selectors into Tier 0 cache."""
    from applypilot.learning.trace_analyzer import analyze_and_promote_traces
    conn = _get_db()
    return analyze_and_promote_traces(conn=conn)


def run_server():
    """Start the FastMCP stdio server."""
    mcp.run()


if __name__ == "__main__":
    run_server()
