"""Tier 0: Selector Replay Engine (0 LLM Tokens).

Replays verified Playwright locators directly from ats_selector_cache for standard
ATS forms (Greenhouse, Lever, Ashby, Workday, SmartRecruiters) before any AI call.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
from typing import Any
from urllib.parse import urlparse

from applypilot.database import (
    get_connection,
    get_selectors_for_domain,
    record_selector_result,
)
from applypilot.learning.tier0_playbook import (
    detect_form_ats,
    fill_standard_fields_playwright,
    get_tier0_field_mappings,
)

logger = logging.getLogger(__name__)


def compute_page_step_signature(field_identifiers: list[str]) -> str:
    """Compute a deterministic hash of the visible input IDs/labels on the page."""
    normalized = sorted(f.strip().lower() for f in field_identifiers if f)
    raw_str = "|".join(normalized)
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()[:16]


def get_cached_selectors_for_step(
    ats_type: str,
    domain_pattern: str,
    step_signature: str | None = None,
    min_confidence: float = 0.8,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """Retrieve verified cached selectors for an ATS page step."""
    if conn is None:
        conn = get_connection()

    query = """
        SELECT * FROM ats_selector_cache
        WHERE ats_type = ? AND domain_pattern = ?
        AND (page_step_signature = ? OR page_step_signature IS NULL)
        AND COALESCE(confidence_score, 1.0) >= ?
        ORDER BY success_count DESC
    """
    rows = conn.execute(query, (ats_type, domain_pattern, step_signature, min_confidence)).fetchall()
    if not rows:
        return []
    columns = rows[0].keys() if isinstance(rows[0], sqlite3.Row) else [
        "selector_id", "cache_id", "ats_type", "domain_pattern", "step_signature",
        "page_step_signature", "canonical_field_id", "field_type",
        "css_or_aria_selector", "playwright_locator", "action_type", "target_key",
        "transform_rule", "success_count", "failure_count", "confidence_score",
        "last_verified_at", "created_at"
    ]
    return [dict(zip(columns, row)) for row in rows]


def replay_tier0_cached_actions(
    page: Any,
    url: str,
    candidate_profile: dict[str, Any],
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Execute cached selectors directly via Playwright with zero tokens spent.

    Falls through only for fields that failed or have no cached locator.
    """
    ats_type = detect_form_ats(url)
    domain = urlparse(url).netloc.lower()

    # Replay hardcoded baseline playbook + cached database selectors
    result = fill_standard_fields_playwright(
        page=page,
        ats_type=ats_type,
        domain=domain,
        profile=candidate_profile,
        conn=conn,
    )

    return {
        "ats_type": ats_type,
        "domain": domain,
        "filled_fields": result.get("filled", []),
        "failed_fields": result.get("failed", []),
        "unmapped_fields": result.get("unmapped", []),
        "token_cost": 0,
    }
