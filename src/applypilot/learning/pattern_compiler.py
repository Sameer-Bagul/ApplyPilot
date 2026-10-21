"""Stage 7: Pattern Compiler & Cache Promoter (applypilot learn).

Analyzes telemetry logs from apply execution (apply_trace.jsonl) and promotes
verified selectors and form mappings with validation_passed=True into
ats_selector_cache and pattern_rules to minimize future AI token usage.
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
    store_selector,
)

logger = logging.getLogger(__name__)

DEFAULT_TRACE_LOG = config.LOG_DIR / "apply_trace.jsonl"


def record_apply_trace(ats_type: str, url: str, selector: str,
                       action_type: str, target_key: str,
                       label: str = "",
                       validation_passed: bool = True,
                       log_path: Path | None = None) -> None:
    """Append a telemetry record for a filled form element."""
    path = log_path or DEFAULT_TRACE_LOG
    path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ats_type": ats_type,
        "url": url,
        "selector": selector,
        "action_type": action_type,
        "target_key": target_key,
        "label": label,
        "validation_passed": validation_passed,
    }

    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.debug("Failed writing apply trace entry: %s", e)


def promote_successful_traces(trace_log_path: Path | None = None,
                              conn: Any = None) -> dict[str, Any]:
    """Analyze apply trace log and promote verified mappings to ats_selector_cache.

    Returns:
        {
            "total_processed": int,
            "promoted_count": int,
            "by_ats": dict[str, int],
        }
    """
    path = trace_log_path or DEFAULT_TRACE_LOG
    if not path.exists():
        return {"total_processed": 0, "promoted_count": 0, "by_ats": {}}

    if conn is None:
        conn = get_connection()

    total_processed = 0
    promoted_count = 0
    by_ats: dict[str, int] = {}

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total_processed += 1
            try:
                data = json.loads(line)
            except Exception:
                continue

            if not data.get("validation_passed"):
                continue

            ats_type = data.get("ats_type", "custom_domain")
            url = data.get("url", "")
            selector = data.get("selector")
            action_type = data.get("action_type", "fill")
            target_key = data.get("target_key")

            if not (selector and target_key):
                continue

            # Extract domain pattern
            domain_pattern = "*"
            if url:
                parsed = urlparse(url)
                host = parsed.netloc.lower()
                if "myworkdayjobs.com" in host:
                    domain_pattern = "*.myworkdayjobs.com"
                elif "greenhouse.io" in host:
                    domain_pattern = "job-boards.greenhouse.io"
                elif "lever.co" in host:
                    domain_pattern = "jobs.lever.co"
                elif "ashbyhq.com" in host:
                    domain_pattern = "jobs.ashbyhq.com"
                else:
                    domain_pattern = host

            # Store in database cache
            selector_id = store_selector(
                ats_type=ats_type,
                domain_pattern=domain_pattern,
                css_or_aria_selector=selector,
                action_type=action_type,
                target_key=target_key,
                conn=conn,
            )
            # Increment success count
            record_selector_result(selector_id, success=True, conn=conn)

            promoted_count += 1
            by_ats[ats_type] = by_ats.get(ats_type, 0) + 1

    return {
        "total_processed": total_processed,
        "promoted_count": promoted_count,
        "by_ats": by_ats,
    }
