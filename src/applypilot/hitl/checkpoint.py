"""Non-blocking form state checkpointing & ATS session cookie vault.

Serializes partially filled form fields, active step index, and cookies so that
the browser worker can be terminated cleanly when waiting for an email reply.
Allows parallel workers to proceed with subsequent jobs without locking RAM.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from applypilot import config
from applypilot.database import (
    get_connection,
    get_session_vault,
    save_session_vault,
)

logger = logging.getLogger(__name__)

SESSIONS_DIR = config.APP_DIR / "ats_sessions"


def serialize_form_checkpoint(page_url: str,
                              step_index: int,
                              filled_fields: dict[str, Any],
                              unresolved_questions: list[dict],
                              extra_state: dict | None = None) -> dict:
    """Serialize full DOM form state into a checkpoint dictionary."""
    return {
        "page_url": page_url,
        "step_index": step_index,
        "filled_fields": filled_fields,
        "unresolved_questions": unresolved_questions,
        "extra_state": extra_state or {},
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }


def save_browser_session_cookies(cookies: list[dict], ats_type: str, company_domain: str,
                                account_email: str | None = None,
                                storage_dir: Path | None = None,
                                conn: sqlite3.Connection | None = None) -> str:
    """Persist browser cookies/localStorage to disk and register in ats_session_vault."""
    out_dir = storage_dir or SESSIONS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_domain = company_domain.replace("/", "_").replace(":", "_")
    state_file = out_dir / f"{ats_type}_{safe_domain}.json"

    payload = {
        "ats_type": ats_type,
        "company_domain": company_domain,
        "account_email": account_email,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "cookies": cookies,
    }

    state_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    save_session_vault(
        ats_type=ats_type,
        company_domain=company_domain,
        storage_state_path=str(state_file),
        account_email=account_email,
        conn=conn,
    )
    return str(state_file)


def load_browser_session_cookies(ats_type: str, company_domain: str,
                                conn: sqlite3.Connection | None = None) -> list[dict] | None:
    """Retrieve saved cookies for an ATS domain if session is valid."""
    vault = get_session_vault(ats_type, company_domain, conn=conn)
    if not vault or not vault.get("session_valid"):
        return None

    path_str = vault.get("storage_state_path")
    if not path_str:
        return None

    state_file = Path(path_str)
    if not state_file.exists():
        return None

    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
        return data.get("cookies", [])
    except Exception as e:
        logger.debug("Failed reading cookies from %s: %s", state_file, e)
        return None


async def replay_checkpoint_playwright(page, checkpoint: dict) -> dict:
    """Replay saved field values on the page in milliseconds.

    Returns:
        {"replayed_count": int, "skipped_count": int, "failed_count": int}
    """
    filled_fields = checkpoint.get("filled_fields", {})
    replayed = 0
    skipped = 0
    failed = 0

    for selector_or_key, val in filled_fields.items():
        if not val:
            continue

        # If key starts with input/select/textarea, it's a DOM selector
        selector = selector_or_key
        try:
            loc = page.locator(selector).first
            if await loc.is_visible(timeout=300):
                current_val = await loc.input_value() if await loc.evaluate("e => 'value' in e") else ""
                if current_val and current_val.strip() == str(val).strip():
                    skipped += 1
                    continue
                from applypilot.apply.human_input import human_type
                await human_type(loc, str(val), page=page)
                replayed += 1
            else:
                skipped += 1
        except Exception as e:
            logger.debug("Checkpoint replay failed for %s: %s", selector, e)
            failed += 1

    return {
        "replayed_count": replayed,
        "skipped_count": skipped,
        "failed_count": failed,
    }
