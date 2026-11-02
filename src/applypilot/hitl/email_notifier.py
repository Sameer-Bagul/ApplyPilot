"""Outbound Email HITL Notifier.

Batches unresolved screening questions and obstacles into a structured,
mobile-friendly email dispatched via Gmail API. Checkpoints the job state
and parks it cleanly so the worker can continue to other jobs in parallel.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import sqlite3
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from applypilot import config
from applypilot.database import (
    create_hitl_ticket,
    get_connection,
    transition_state,
)

logger = logging.getLogger(__name__)

GMAIL_MCP_DIR = Path.home() / ".gmail-mcp"
CREDENTIALS_PATH = GMAIL_MCP_DIR / "credentials.json"


def format_hitl_email_subject(ticket_id: int, job: dict, question_count: int) -> str:
    """Generate deterministic subject line for thread tracking."""
    title = job.get("title", "Job Application")[:40]
    company = job.get("company") or job.get("site") or "Company"
    score = job.get("fit_score", "N/A")
    return f"[ApplyPilot HITL #{ticket_id}] {question_count} Questions: {title} @ {company} (Score: {score}/10)"


def format_hitl_email_body(ticket_id: int, job: dict, questions: list[dict],
                           step_info: str = "Step 1") -> tuple[str, str]:
    """Format plaintext and HTML email bodies for user reply.

    Returns:
        (text_body, html_body)
    """
    title = job.get("title", "Position")
    company = job.get("company") or job.get("site") or "Employer"
    url = job.get("application_url") or job.get("url", "")
    score = job.get("fit_score", "N/A")

    # Plaintext
    text_lines = [
        f"ApplyPilot HITL Escalation — Ticket #{ticket_id}",
        "=" * 60,
        f"Role: {title}",
        f"Company: {company}",
        f"Match Score: {score}/10",
        f"Application Link: {url}",
        f"Progress: Paused on {step_info} awaiting your input.",
        "",
        "QUESTIONS REQUIRING YOUR INPUT:",
        "-" * 60,
    ]

    # HTML
    html_q_blocks = []

    for idx, q in enumerate(questions, start=1):
        field_id = q.get("field_id", f"field_{idx}")
        label = q.get("label", "Question")
        ftype = q.get("field_type", "text")
        required = "Required" if q.get("required") else "Optional"
        options = q.get("options") or []
        draft = q.get("suggested_draft") or ""

        # Plaintext block
        text_lines.append(f"\nQ{idx} [{required} | {ftype.capitalize()}]")
        text_lines.append(f"Label: {label}")
        if options:
            text_lines.append("Options:")
            for opt_idx, opt in enumerate(options):
                letter = chr(ord('A') + opt_idx)
                text_lines.append(f"  {letter}) {opt}")
        if draft:
            text_lines.append(f"Suggested Draft (from profile): {draft}")

        # HTML block
        options_html = ""
        if options:
            options_items = "".join([f"<li><strong>{chr(ord('A') + i)})</strong> {opt}</li>" for i, opt in enumerate(options)])
            options_html = f"<ul style='margin: 6px 0; padding-left: 20px; color: #374151;'>{options_items}</ul>"

        draft_html = ""
        if draft:
            draft_html = f"<div style='margin-top: 6px; padding: 8px; background: #f3f4f6; border-radius: 4px; font-size: 13px;'><strong>Suggested Draft:</strong> <code>{draft}</code></div>"

        html_q_blocks.append(f"""
        <div style="margin-bottom: 20px; padding: 14px; border: 1px solid #e5e7eb; border-radius: 8px; background: #fafafa;">
            <div style="font-weight: 600; color: #111827; margin-bottom: 4px;">
                Q{idx} <span style="font-size: 12px; font-weight: normal; color: #6b7280;">[{required} | {ftype.capitalize()}]</span>
            </div>
            <div style="color: #1f2937; margin-bottom: 8px;">{label}</div>
            {options_html}
            {draft_html}
        </div>
        """)

    text_lines.extend([
        "",
        "=" * 60,
        "HOW TO REPLY:",
        "Simply reply to this email with your answers by question number, e.g.:",
        "  Q1: A",
        "  Q2: APPROVE  (or write custom text)",
        "",
        "Your answers will be saved to your permanent knowledge base and the application",
        "will resume and submit automatically without asking again.",
    ])

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.5; color: #1f2937; max-width: 650px; margin: 0 auto; padding: 20px;">
        <div style="background: #2563eb; color: #ffffff; padding: 16px 20px; border-radius: 8px 8px 0 0;">
            <h2 style="margin: 0; font-size: 18px;">ApplyPilot — Action Needed (Ticket #{ticket_id})</h2>
            <div style="font-size: 14px; opacity: 0.9; margin-top: 4px;">{title} @ {company} (Score: {score}/10)</div>
        </div>
        <div style="border: 1px solid #e5e7eb; border-top: none; padding: 20px; border-radius: 0 0 8px 8px;">
            <p style="margin-top: 0;">The autonomous applicant has paused on <strong>{step_info}</strong> because it encountered questions requiring your verification:</p>
            {"".join(html_q_blocks)}
            <div style="background: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 6px; padding: 12px 16px; margin-top: 20px;">
                <h4 style="margin: 0 0 6px 0; color: #065f46;">How to Reply from your phone or inbox:</h4>
                <div style="font-size: 13px; color: #047857;">
                    Reply to this thread with your selections:<br>
                    <code>Q1: A</code><br>
                    <code>Q2: APPROVE</code> (or type custom text)<br><br>
                    <em>Your answers are permanently stored so you won't be asked again.</em>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    return "\n".join(text_lines), html_body


def send_gmail_api(to_email: str, subject: str, text_content: str, html_content: str,
                   thread_id: str | None = None) -> tuple[bool, str | None, str | None]:
    """Send an email using Gmail OAuth access token.

    Returns:
        (success, message_id, thread_id)
    """
    if not CREDENTIALS_PATH.exists():
        logger.warning("Gmail credentials not found at %s. Mocking send.", CREDENTIALS_PATH)
        return True, "mock_msg_123", "mock_thread_123"

    try:
        creds_data = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
        access_token = creds_data.get("access_token")
        if not access_token:
            return False, None, None

        msg = MIMEMultipart("alternative")
        msg["To"] = to_email
        msg["Subject"] = subject
        msg["From"] = "me"
        if thread_id:
            msg["In-Reply-To"] = thread_id
            msg["References"] = thread_id

        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        raw_b64 = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        payload: dict[str, Any] = {"raw": raw_b64}
        if thread_id:
            payload["threadId"] = thread_id

        req = urllib.request.Request(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            msg_id = data.get("id")
            th_id = data.get("threadId")
            return True, msg_id, th_id

    except Exception as e:
        logger.error("Failed sending Gmail HITL email: %s", e)
        return False, None, None


def dispatch_hitl_email_and_park(job: dict,
                                 unanswered_questions: list[dict],
                                 dom_checkpoint: dict | None = None,
                                 recipient_email: str | None = None,
                                 conn: sqlite3.Connection | None = None) -> int:
    """Batch unanswered questions, send HITL email, and park job cleanly.

    Returns:
        ticket_id
    """
    if conn is None:
        conn = get_connection()

    job_url = job.get("url") or job.get("application_url", "")
    to_email = recipient_email or job.get("applicant_email") or "me"

    # Step 1: Create initial ticket row
    ticket_id = create_hitl_ticket(
        job_url=job_url,
        unanswered_questions=unanswered_questions,
        dom_checkpoint=dom_checkpoint,
        conn=conn,
    )

    # Step 2: Format email
    subject = format_hitl_email_subject(ticket_id, job, len(unanswered_questions))
    step_info = f"Step {dom_checkpoint.get('step_index', 1)}" if dom_checkpoint else "Application Form"
    text_body, html_body = format_hitl_email_body(ticket_id, job, unanswered_questions, step_info)

    # Step 3: Dispatch via Gmail
    success, msg_id, th_id = send_gmail_api(to_email, subject, text_body, html_body)

    # Step 4: Update ticket with Gmail IDs
    if msg_id or th_id:
        conn.execute(
            "UPDATE hitl_tickets SET gmail_message_id = ?, gmail_thread_id = ? WHERE ticket_id = ?",
            (msg_id, th_id, ticket_id),
        )
        conn.commit()

    # Step 5: Park job non-blockingly
    transition_state(
        conn=conn,
        job_url=job_url,
        to_state="parked_awaiting_email",
        reason=f"HITL email dispatched (Ticket #{ticket_id})",
        metadata={"ticket_id": ticket_id, "questions_count": len(unanswered_questions)},
    )

    logger.info("Parked job %s awaiting email reply (Ticket #%d)", job_url[:60], ticket_id)
    return ticket_id


def park_and_notify_user(
    job_id: str | None = None,
    lead_id: str | None = None,
    company: str = "",
    role_title: str = "",
    job_url: str = "",
    blocker_type: str = "screening_question",
    unknown_questions: list[dict] | None = None,
    dom_checkpoint: dict | None = None,
    recipient_email: str | None = None,
    conn: sqlite3.Connection | None = None,
    mock: bool = False,
) -> int:
    """Park an application or lead and dispatch a structured HITL notification email to user.

    Supports both Track A (outreach / cold mailer) and Track B (portal form applier).
    """
    if conn is None:
        conn = get_connection()

    questions = unknown_questions or []
    target_url = job_url or (f"https://applypilot.local/leads/{lead_id}" if lead_id else f"https://applypilot.local/jobs/{job_id}")

    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO jobs (url, title, company, site, state)
            VALUES (?, ?, ?, 'hitl', 'discovered')
            """,
            (target_url, role_title or "Role", company or "Company"),
        )
        conn.commit()
    except Exception:
        pass

    ticket_id = create_hitl_ticket(
        job_url=target_url,
        unanswered_questions=questions,
        dom_checkpoint=dom_checkpoint,
        conn=conn,
    )

    try:
        conn.execute(
            """
            UPDATE hitl_tickets
            SET job_id = ?, lead_id = ?, company = ?, role_title = ?, blocker_type = ?, questions_json = ?
            WHERE ticket_id = ?
            """,
            (
                job_id,
                lead_id,
                company,
                role_title,
                blocker_type,
                json.dumps(questions),
                ticket_id,
            ),
        )
        conn.commit()
    except Exception as e:
        logger.debug("Hitl ticket extended fields notice: %s", e)

    job_dict = {
        "title": role_title or "Role",
        "company": company or "Company",
        "url": target_url,
        "fit_score": "N/A",
    }
    step_info = f"Step {dom_checkpoint.get('step_index', 1)}" if dom_checkpoint else blocker_type
    subject = f"[ApplyPilot HITL #AP-{ticket_id}] Action Required: {len(questions)} Missing Answer(s) for {role_title or 'Position'} at {company or 'Company'}"
    text_body, html_body = format_hitl_email_body(ticket_id, job_dict, questions, step_info)

    to_email = recipient_email or "me"
    if not mock:
        success, msg_id, th_id = send_gmail_api(to_email, subject, text_body, html_body)
    else:
        success, msg_id, th_id = True, "mock_msg_hitl", "mock_thread_hitl"

    if msg_id or th_id:
        try:
            conn.execute(
                "UPDATE hitl_tickets SET gmail_message_id = ?, gmail_thread_id = ? WHERE ticket_id = ?",
                (msg_id, th_id, ticket_id),
            )
            conn.commit()
        except Exception:
            pass

    if job_url:
        try:
            transition_state(
                conn=conn,
                job_url=job_url,
                to_state="parked_awaiting_email",
                reason=f"HITL email dispatched (Ticket #AP-{ticket_id})",
                metadata={"ticket_id": ticket_id, "questions_count": len(questions)},
            )
        except Exception as e:
            logger.debug("Job state transition notice: %s", e)

    if lead_id:
        try:
            conn.execute(
                "UPDATE recruiter_leads SET outreach_status = 'parked_hitl', gmail_thread_id = ? WHERE lead_id = ?",
                (th_id, lead_id),
            )
            conn.commit()
        except Exception as e:
            logger.debug("Lead status transition notice: %s", e)

    logger.info("Dispatched HITL email for ticket #AP-%d", ticket_id)
    return ticket_id
