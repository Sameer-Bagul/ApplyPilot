"""Inbound Email Reply Parser & Knowledge Expander.

Parses user replies to [ApplyPilot HITL #ID] threads, maps answers like
'Q1: A' or 'Q2: APPROVE' onto unanswered_questions schemas, validates field
constraints, permanently stores facts in qa_knowledge_base, and transitions
parked jobs to 'queued_resume' for parallel worker revisit.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from typing import Any

from applypilot.database import (
    get_connection,
    get_hitl_ticket,
    resolve_hitl_ticket,
    store_qa,
    transition_state,
)
from applypilot.learning.tier1_semantic_qa import (
    compute_question_hash,
    match_dropdown_option,
    normalize_question,
)

logger = logging.getLogger(__name__)


def strip_email_quoted_headers(body: str) -> str:
    """Remove email reply quotes and headers (e.g. '> ...' or 'On ... wrote:')."""
    if not body:
        return ""

    lines = []
    for line in body.splitlines():
        trimmed = line.strip()
        # Drop lines starting with quote marker >
        if trimmed.startswith(">"):
            continue
        # Drop standard email thread separation markers
        if re.match(r"(?i)^On\s+.+wrote:\s*$", trimmed):
            break
        if re.match(r"(?i)^-+Original Message-+", trimmed):
            break
        lines.append(line)

    return "\n".join(lines).strip()


def parse_reply_answers(reply_text: str) -> dict[int, str]:
    """Extract answers mapped by question number (1-indexed).

    Matches formats like:
      Q1: A
      Q2 - APPROVE
      q1: Yes
      Q3: Over 4 years using Kubernetes and ArgoCD
    """
    clean_text = strip_email_quoted_headers(reply_text)
    pattern = re.compile(r"(?i)\bQ(\d+)\s*[:\-]\s*(.+?)(?=(?:\bQ\d+\s*[:\-]|\Z))", re.DOTALL)

    answers: dict[int, str] = {}
    for match in pattern.finditer(clean_text):
        q_num = int(match.group(1))
        ans_val = match.group(2).strip()
        # Clean inline newlines inside single answer
        ans_clean = " ".join(ans_val.split())
        answers[q_num] = ans_clean

    return answers


def resolve_answer_for_question(user_ans: str, question_spec: dict) -> tuple[str | None, str | None]:
    """Resolve user shorthand into a canonical answer string.

    Returns:
        (resolved_value, error_message)
    """
    raw = user_ans.strip()
    options: list[str] = question_spec.get("options") or []
    draft: str = question_spec.get("suggested_draft") or ""
    required: bool = bool(question_spec.get("required"))
    max_len: int | None = question_spec.get("max_length")

    if not raw:
        if required:
            return None, "Required field was left empty."
        return "", None

    # Handle APPROVE macro for suggested drafts
    if raw.upper() == "APPROVE" or raw.upper() == "APPROVED":
        if draft:
            return draft, None
        return raw, None

    # Handle single letter choices (A, B, C, D) on dropdown options
    if options and re.match(r"^[A-Za-z]\)?$", raw):
        letter_idx = ord(raw[0].upper()) - ord('A')
        if 0 <= letter_idx < len(options):
            return options[letter_idx], None
        return None, f"Option {raw[0].upper()} is out of range."

    # If options exist, attempt fuzzy match
    if options:
        matched = match_dropdown_option(raw, options)
        if matched:
            return matched, None
        return None, f"'{raw}' does not match any valid dropdown options: {options}"

    # Handle character limits
    if max_len and len(raw) > max_len:
        # Trim safely at word boundary
        trimmed = raw[:max_len].rsplit(" ", 1)[0]
        return trimmed, None

    return raw, None


def process_hitl_ticket_reply(ticket_id: int, reply_body: str,
                              conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    """Ingest user reply for a HITL ticket, update DB, and requeue job.

    Returns:
        {
            "success": bool,
            "resolved_answers": dict[str, str],
            "errors": dict[int, str],
            "job_url": str,
        }
    """
    if conn is None:
        conn = get_connection()

    ticket = get_hitl_ticket(ticket_id, conn=conn)
    if not ticket:
        return {"success": False, "error": f"Ticket #{ticket_id} not found"}

    unanswered_questions: list[dict] = ticket.get("unanswered_questions", [])
    job_url: str = ticket.get("job_url", "")

    raw_answers = parse_reply_answers(reply_body)
    if not raw_answers:
        return {"success": False, "error": "No Q1, Q2 answers found in email reply"}

    resolved_map: dict[str, str] = {}
    errors: dict[int, str] = {}

    for idx, q_spec in enumerate(unanswered_questions, start=1):
        if idx not in raw_answers:
            if q_spec.get("required"):
                errors[idx] = "Missing required answer in reply."
            continue

        user_str = raw_answers[idx]
        val, err = resolve_answer_for_question(user_str, q_spec)
        if err:
            errors[idx] = err
        elif val is not None:
            resolved_map[q_spec.get("label", f"Q{idx}")] = val

            # Permanently promote to qa_knowledge_base
            norm_q = normalize_question(q_spec.get("label", ""))
            q_hash = compute_question_hash(norm_q)
            store_qa(
                question=q_spec.get("label", ""),
                answer=val,
                source="human_email",
                canonical_question=norm_q,
                question_hash=q_hash,
                field_type=q_spec.get("field_type"),
                job_url=job_url,
                conn=conn,
            )

    # If any required questions had errors, ticket remains open
    if errors:
        return {
            "success": False,
            "resolved_answers": resolved_map,
            "errors": errors,
            "job_url": job_url,
        }

    # Mark ticket resolved
    resolve_hitl_ticket(ticket_id, status="resolved", conn=conn)

    # Transition job to queued_resume so parallel workers revisit it
    transition_state(
        conn=conn,
        job_url=job_url,
        to_state="queued_resume",
        reason=f"HITL reply received for ticket #{ticket_id}",
        metadata={"ticket_id": ticket_id, "resolved_keys": list(resolved_map.keys())},
    )
    conn.execute(
        "UPDATE jobs SET apply_status = NULL WHERE url = ?",
        (job_url,),
    )
    conn.commit()

    logger.info("Ticket #%d resolved. Job %s moved to queued_resume", ticket_id, job_url[:60])
    return {
        "success": True,
        "resolved_answers": resolved_map,
        "errors": {},
        "job_url": job_url,
    }


def sync_email_hitl_replies(poll_window_hours: int = 48,
                            conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    """Poll Gmail for user replies to pending HITL tickets.

    Parses user answers, updates qa_knowledge, resolves the tickets,
    and transitions the associated jobs to queued_resume.

    Returns:
        {
            "resolved_tickets": list[int],
            "requeued_jobs": list[str],
            "errors": list[str],
        }
    """
    import os
    import json as _json
    import urllib.parse as _parse
    import urllib.request as _request
    from pathlib import Path
    from applypilot.database import get_pending_hitl_tickets

    if conn is None:
        conn = get_connection()

    pending = get_pending_hitl_tickets(conn=conn)
    if not pending:
        return {"resolved_tickets": [], "requeued_jobs": [], "errors": []}

    gmail_dir = Path(os.environ.get("GMAIL_MCP_DIR", str(Path.home() / ".gmail-mcp")))
    creds_path = gmail_dir / "credentials.json"
    if not creds_path.exists():
        logger.debug("Gmail credentials not configured for HITL sync.")
        return {"resolved_tickets": [], "requeued_jobs": [], "errors": ["Gmail credentials not configured."]}

    try:
        creds = _json.loads(creds_path.read_text(encoding="utf-8"))
        token = creds.get("access_token")
    except Exception as e:
        return {"resolved_tickets": [], "requeued_jobs": [], "errors": [str(e)]}

    resolved_tickets: list[int] = []
    requeued_jobs: list[str] = []
    errors: list[str] = []

    def _extract_plain_text_from_payload(payload: dict) -> str:
        """Recursively extract plain text body from a Gmail message payload."""
        import base64
        body_data = payload.get("body", {}).get("data")
        if body_data:
            try:
                return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
            except Exception:
                pass

        parts = payload.get("parts", [])
        for part in parts:
            mime = part.get("mimeType", "")
            if mime == "text/plain":
                part_data = part.get("body", {}).get("data")
                if part_data:
                    try:
                        return base64.urlsafe_b64decode(part_data).decode("utf-8", errors="replace")
                    except Exception:
                        pass
            elif "parts" in part:
                nested = _extract_plain_text_from_payload(part)
                if nested:
                    return nested
        return ""

    for ticket in pending:
        t_id = ticket["ticket_id"]
        th_id = ticket.get("gmail_thread_id")
        subject_query = f"subject:\"ApplyPilot HITL #{t_id}\""

        q = f"thread:{th_id}" if th_id else subject_query
        q_enc = _parse.quote(q)
        url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages?q={q_enc}&maxResults=10"

        try:
            req = _request.Request(url, headers={"Authorization": f"Bearer {token}"})
            with _request.urlopen(req, timeout=15) as resp:
                res_data = _json.loads(resp.read().decode("utf-8"))
                messages = res_data.get("messages", [])

            for m in reversed(messages):
                m_id = m.get("id")
                if m_id == ticket.get("gmail_message_id"):
                    continue

                d_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{m_id}?format=full"
                d_req = _request.Request(d_url, headers={"Authorization": f"Bearer {token}"})
                with _request.urlopen(d_req, timeout=15) as d_resp:
                    d_data = _json.loads(d_resp.read().decode("utf-8"))
                    payload_text = _extract_plain_text_from_payload(d_data.get("payload", {}))
                    body_content = payload_text.strip() if payload_text else d_data.get("snippet", "")

                if body_content and ("q1" in body_content.lower() or "approve" in body_content.lower()):
                    result = process_hitl_ticket_reply(t_id, body_content, conn=conn)
                    if result.get("success"):
                        resolved_tickets.append(t_id)
                        requeued_jobs.append(result.get("job_url", ""))
                        break
                    elif result.get("errors"):
                        errors.append(f"Ticket #{t_id}: {result['errors']}")

        except Exception as e:
            logger.debug("Failed checking thread for ticket #%d: %s", t_id, e)
            errors.append(f"Ticket #{t_id}: {str(e)}")

    return {
        "resolved_tickets": resolved_tickets,
        "requeued_jobs": requeued_jobs,
        "errors": errors,
    }
