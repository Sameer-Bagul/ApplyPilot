"""Post-run Trace Analyzer & Compiler (applypilot learn).

Analyzes execution telemetry from ~/.applypilot/logs/apply_trace.jsonl after each
run and promotes verified Playwright locators into ats_selector_cache (Tier 0)
and learned answers into qa_knowledge (Tier 1) and qa_fts.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from applypilot import config
from applypilot.database import (
    get_connection,
    record_selector_result,
    store_qa,
    store_selector,
)
from applypilot.learning.canonical_matcher import normalize_field_label
from applypilot.learning.pattern_compiler import promote_successful_traces, record_apply_trace

logger = logging.getLogger(__name__)

DEFAULT_TRACE_LOG = config.LOG_DIR / "apply_trace.jsonl"


def analyze_and_promote_traces(
    trace_log_path: Path | None = None,
    conn: Any = None,
) -> dict[str, Any]:
    """Analyze apply trace records and promote verified items to Tier 0 and Tier 1.

    Returns:
        {
            "total_processed": int,
            "promoted_selectors": int,
            "promoted_qa": int,
            "by_ats": dict[str, int],
        }
    """
    path = trace_log_path or DEFAULT_TRACE_LOG
    if not path.exists():
        return {
            "total_processed": 0,
            "promoted_selectors": 0,
            "promoted_qa": 0,
            "by_ats": {},
        }

    if conn is None:
        conn = get_connection()

    promoted_selectors = 0
    promoted_qa = 0
    by_ats: dict[str, int] = {}
    total_processed = 0

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total_processed += 1
            try:
                entry = json.loads(line)
            except Exception:
                continue

            if not entry.get("validation_passed", False):
                continue

            ats = entry.get("ats_type", "unknown")
            selector = entry.get("selector")
            action = entry.get("action_type", "fill")
            target_key = entry.get("target_key", "")
            label = entry.get("label", "")
            url = entry.get("url", "")
            domain = urlparse(url).netloc.lower() if url else ats

            # Promote selector to Tier 0 ats_selector_cache
            if selector and target_key:
                store_selector(
                    ats_type=ats,
                    domain_pattern=domain,
                    css_or_aria_selector=selector,
                    action_type=action,
                    target_key=target_key,
                    conn=conn,
                )
                promoted_selectors += 1
                by_ats[ats] = by_ats.get(ats, 0) + 1

            # Promote novel Q&A pairs to Tier 1 qa_knowledge and qa_fts
            value = entry.get("value")
            if label and value and not target_key.startswith("profile."):
                norm_q = normalize_field_label(label)
                store_qa(
                    question=label,
                    answer=str(value),
                    source="trace_compiler",
                    canonical_question=norm_q,
                    conn=conn,
                )
                try:
                    conn.execute(
                        "INSERT INTO qa_fts (question_key, canonical_question, question_text, answer_text) "
                        "VALUES (?, ?, ?, ?)",
                        (norm_q, norm_q, label, str(value)),
                    )
                    conn.commit()
                except Exception:
                    pass
                promoted_qa += 1

    return {
        "total_processed": total_processed,
        "promoted_selectors": promoted_selectors,
        "promoted_qa": promoted_qa,
        "by_ats": by_ats,
    }
