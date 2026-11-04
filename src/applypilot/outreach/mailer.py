"""Part 2A: Automated HR & Founder Cold Mailer (Track A Execution Engine).

Drafts or auto-sends hyper-tailored emails to HR/founders citing exact social
post URLs, incorporates verified answers from profile and qa_knowledge,
attaches tailored resume PDFs, respects DUAL_ATTACK sequencing, and triggers
HITL parking if unknown questions arise.
"""

from __future__ import annotations

import base64
import json
import logging
import mimetypes
import os
import re
import sqlite3
import urllib.request
from datetime import datetime, timezone
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from applypilot import config
from applypilot.database import (
    get_connection,
    get_recruiter_leads,
    update_recruiter_lead_status,
)
from applypilot.hitl.email_notifier import (
    CREDENTIALS_PATH,
    park_and_notify_user,
    send_gmail_api,
)

logger = logging.getLogger(__name__)


def _load_profile() -> dict[str, Any]:
    """Load user's candidate profile from config.PROFILE_PATH."""
    p_path = config.PROFILE_PATH
    if p_path.exists():
        try:
            return json.loads(p_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "name": "Candidate",
        "email": "candidate@example.com",
        "title": "Software Engineer",
        "summary": "Experienced Software Engineer with a focus on autonomous agents and backend systems.",
        "skills": ["Python", "FastAPI", "Playwright", "Docker", "PostgreSQL", "LLM Integration"],
        "github": "https://github.com",
        "linkedin": "https://linkedin.com",
    }


def find_resume_pdf(role_title: str = "", company_name: str = "") -> Path | None:
    """Find the best matching tailored resume PDF or default base resume."""
    tailored_dir = getattr(config, "TAILORED_DIR", Path.home() / ".applypilot" / "tailored_resumes")
    if tailored_dir.exists():
        # Look for company tailored resumes
        for pdf_file in tailored_dir.glob("*.pdf"):
            if company_name and company_name.lower() in pdf_file.name.lower():
                return pdf_file
        first_pdf = next(tailored_dir.glob("*.pdf"), None)
        if first_pdf:
            return first_pdf

    base_pdf = getattr(config, "RESUME_PDF_PATH", Path.home() / ".applypilot" / "resume.pdf")
    if base_pdf and base_pdf.exists():
        return base_pdf

    # Check root workspace for CV
    root = Path.cwd()
    for root_pdf in root.glob("*.pdf"):
        if "cv" in root_pdf.name.lower() or "resume" in root_pdf.name.lower():
            return root_pdf

    return None


def extract_special_instructions(post_text: str) -> dict[str, Any]:
    """Inspect social post text for explicit application instructions."""
    instructions: dict[str, Any] = {}
    if not post_text:
        return instructions

    lower = post_text.lower()

    # Subject line instruction
    subject_match = re.search(r"subject(?:\s+line)?[:\s]+[\"']?([^\"'\n\r]+)[\"']?", post_text, re.IGNORECASE)
    if subject_match:
        instructions["required_subject"] = subject_match.group(1).strip()

    # Question checks
    if any(k in lower for k in ("notice period", "how soon", "availability", "join date")):
        instructions["needs_notice_period"] = True
    if any(k in lower for k in ("ctc", "salary expectation", "compensation", "rate")):
        instructions["needs_salary"] = True
    if any(k in lower for k in ("github", "repo", "portfolio", "code sample")):
        instructions["needs_portfolio"] = True
    if any(k in lower for k in ("location", "based in", "relocate")):
        instructions["needs_location"] = True

    return instructions


def create_gmail_draft(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str,
    attachment_path: Path | None = None,
) -> tuple[bool, str | None]:
    """Create a draft email in the user's Gmail account via Gmail API."""
    if not CREDENTIALS_PATH.exists():
        logger.info("Gmail credentials not found at %s. Mocking Gmail Draft.", CREDENTIALS_PATH)
        return True, "mock_draft_id_123"

    try:
        creds = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
        access_token = creds.get("access_token")
        if not access_token:
            return False, None

        msg = MIMEMultipart("mixed")
        msg["To"] = to_email
        msg["Subject"] = subject

        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(text_body, "plain", "utf-8"))
        alt.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(alt)

        if attachment_path and attachment_path.exists():
            ctype, encoding = mimetypes.guess_type(str(attachment_path))
            ctype = ctype or "application/octet-stream"
            part = MIMEApplication(attachment_path.read_bytes(), Name=attachment_path.name)
            part["Content-Disposition"] = f'attachment; filename="{attachment_path.name}"'
            msg.attach(part)

        raw_b64 = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        payload = {"message": {"raw": raw_b64}}

        req = urllib.request.Request(
            "https://gmail.googleapis.com/gmail/v1/users/me/drafts",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            draft_id = data.get("id")
            return True, draft_id

    except Exception as e:
        logger.error("Failed creating Gmail draft: %s", e)
        return False, None


def compose_cold_email(
    lead: dict[str, Any],
    profile: dict[str, Any],
    special_instructions: dict[str, Any],
    has_submitted_portal: bool = False,
) -> tuple[str, str, str]:
    """Compose hyper-tailored subject, plaintext body, and HTML body."""
    candidate_name = profile.get("name", "Applicant")
    role = lead.get("role_title", "Software Engineer")
    company = lead.get("company_name", "your team")
    platform = lead.get("source_platform", "social post").capitalize()
    post_url = lead.get("source_post_url", "")
    contact_type = lead.get("contact_type", "recruiter")

    # 1. Subject line
    if special_instructions.get("required_subject"):
        subject = special_instructions["required_subject"]
        subject = subject.replace("[Name]", candidate_name).replace("[Your Name]", candidate_name)
    else:
        subject = f"{role} Application — {candidate_name}"

    # 2. Salutation
    salutation = "Hi there"
    if contact_type == "founder":
        salutation = "Hi,"
    elif contact_type == "recruiter":
        salutation = "Hi Recruitment Team,"

    # 3. Intro referencing exact post
    post_citation = f"I saw your recent post on {platform}"
    if post_url:
        post_citation += f" ({post_url})"
    post_citation += f" regarding the {role} position."

    # 4. Dual Attack clause
    dual_attack_clause = ""
    if has_submitted_portal:
        dual_attack_clause = (
            "I've also submitted my formal application through your official career portal, "
            "and wanted to reach out directly to share my portfolio and tailored resume."
        )

    # 5. Body paragraphs
    summary = profile.get("summary") or "I specialize in backend engineering, autonomous systems, and high-performance APIs."
    github = profile.get("github") or ""
    linkedin = profile.get("linkedin") or ""

    text_body = f"""{salutation}

{post_citation}
{dual_attack_clause}

{summary}

A few highlights relevant to {company}:
- Strong foundation in scalable architectures, zero-token caching, and resilient automation
- Hands-on experience building production-grade services and LLM agent pipelines
- Active code repository: {github}
- LinkedIn Profile: {linkedin}

I have attached my tailored resume (PDF) for your review. I would welcome the opportunity to connect and discuss how my background aligns with your engineering goals.

Best regards,
{candidate_name}
{profile.get('email', '')}
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1f2937;">
<p>{salutation}</p>
<p>{post_citation}<br>
{f"<em>{dual_attack_clause}</em>" if dual_attack_clause else ""}</p>
<p>{summary}</p>
<p><strong>A few highlights:</strong></p>
<ul>
    <li>Strong foundation in scalable architectures and resilient automation</li>
    <li>Hands-on experience building production-grade backend and AI agent pipelines</li>
    <li>GitHub: <a href="{github}">{github}</a></li>
    <li>LinkedIn: <a href="{linkedin}">{linkedin}</a></li>
</ul>
<p>I have attached my tailored resume for your review. I would welcome the opportunity to connect and discuss how my background aligns with your engineering goals.</p>
<p>Best regards,<br>
<strong>{candidate_name}</strong><br>
<span style="color: #6b7280; font-size: 13px;">{profile.get('email', '')}</span></p>
</body>
</html>
"""
    return subject, text_body, html_body


def run_hr_outreach(
    mode: str = "draft",
    limit: int = 10,
    min_score: int = 70,
    conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Execute outreach for queued recruiter leads.

    Args:
        mode: "draft" (create Gmail Draft) or "auto_send" (send via Gmail API).
        limit: Max leads to process.
        min_score: Minimum match score threshold.
        conn: Optional SQLite connection.

    Returns:
        Summary dict of processed leads.
    """
    if conn is None:
        conn = get_connection()

    leads = get_recruiter_leads(status="queued", limit=limit, conn=conn)
    profile = _load_profile()

    processed = 0
    drafted = 0
    sent = 0
    parked_hitl = 0
    skipped_dual_attack = 0

    for lead in leads:
        lead_id = lead["lead_id"]
        to_email = lead["contact_email"]
        company = lead.get("company_name") or "Company"
        role_title = lead.get("role_title") or "Software Engineer"
        evidence = lead.get("evidence_snippet") or ""
        route = lead.get("execution_route") or "EMAIL_ONLY"

        # Check DUAL_ATTACK sequencing
        has_submitted_portal = False
        if route == "DUAL_ATTACK":
            # Check if associated job has been submitted on portal
            job_row = conn.execute(
                "SELECT state FROM jobs WHERE company = ? OR title = ? ORDER BY rowid DESC LIMIT 1",
                (company, role_title),
            ).fetchone()
            if job_row and job_row[0] in ("applied", "completed"):
                has_submitted_portal = True
            elif job_row and job_row[0] not in ("applied", "completed"):
                # Wait for Track B (apply) to submit the portal form first!
                logger.info("Skipping DUAL_ATTACK lead %s until portal form is submitted first", lead_id)
                skipped_dual_attack += 1
                continue

        # Extract special instructions and questions
        instructions = extract_special_instructions(evidence)

        # Generate LinkedIn connection note if contact LinkedIn URL is present
        contact_li = lead.get("contact_linkedin_url")
        li_note = lead.get("linkedin_connection_note")
        if contact_li and not li_note:
            from applypilot.discovery.bangalore_map_harvester import generate_linkedin_connection_note
            li_note = generate_linkedin_connection_note(
                founder_name=lead.get("contact_name") or "Founder",
                startup_name=company,
                sector=None,
                tagline=evidence,
            )
            conn.execute(
                "UPDATE recruiter_leads SET linkedin_connection_note = ? WHERE lead_id = ?",
                (li_note, lead_id),
            )
            conn.commit()

        if to_email and to_email.endswith("@connect.linkedin.com"):
            # LinkedIn connection lead — note is ready for 1-click copying
            update_recruiter_lead_status(lead_id=lead_id, status="note_ready", conn=conn)
            processed += 1
            drafted += 1
            continue

        # Check if instructions require missing information -> HITL guardrail
        missing_questions = []
        if instructions.get("needs_salary") and not profile.get("expected_salary"):
            missing_questions.append({
                "field_id": "expected_salary",
                "label": f"What is your target CTC / compensation for {role_title} at {company}?",
                "field_type": "text",
                "required": True,
            })
        if instructions.get("needs_notice_period") and not profile.get("notice_period"):
            missing_questions.append({
                "field_id": "notice_period",
                "label": f"What is your notice period for {role_title} at {company}?",
                "field_type": "text",
                "required": True,
                "suggested_draft": "Immediate / 2 weeks",
            })

        if missing_questions:
            # Park lead and trigger HITL email notification to user
            logger.info("Parking lead %s due to %d missing questions", lead_id, len(missing_questions))
            park_and_notify_user(
                lead_id=lead_id,
                company=company,
                role_title=role_title,
                unknown_questions=missing_questions,
                conn=conn,
            )
            parked_hitl += 1
            continue

        # Resolve resume attachment
        resume_pdf = find_resume_pdf(role_title=role_title, company_name=company)

        # Compose cold mail
        subject, text_body, html_body = compose_cold_email(
            lead=lead,
            profile=profile,
            special_instructions=instructions,
            has_submitted_portal=has_submitted_portal,
        )

        # Persist draft subject & text body for Admin HITL review
        conn.execute(
            """
            UPDATE recruiter_leads
            SET email_draft_subject = ?, email_draft_body = ?
            WHERE lead_id = ?
            """,
            (subject, text_body, lead_id),
        )
        conn.commit()

        # Execute based on mode
        if mode == "auto_send":
            # Safety gate: check if lead is approved
            row_app = conn.execute("SELECT outreach_status FROM recruiter_leads WHERE lead_id = ?", (lead_id,)).fetchone()
            if row_app and row_app[0] != "approved":
                logger.info("Outreach lead %s not approved by admin; keeping in pending_review", lead_id)
                conn.execute(
                    "UPDATE recruiter_leads SET outreach_status = 'pending_review' WHERE lead_id = ?",
                    (lead_id,),
                )
                conn.commit()
                drafted += 1
                processed += 1
                continue

            success, msg_id, th_id = send_gmail_api(
                to_email=to_email,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
            )
            if success:
                update_recruiter_lead_status(
                    lead_id=lead_id,
                    status="sent",
                    gmail_thread_id=th_id,
                    conn=conn,
                )
                sent += 1
            else:
                update_recruiter_lead_status(lead_id=lead_id, status="error_sending", conn=conn)
        else:
            # Draft mode (Strict Human-in-the-Loop default)
            success, draft_id = create_gmail_draft(
                to_email=to_email,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                attachment_path=resume_pdf,
            )
            status_val = "drafted" if success else "pending_review"
            update_recruiter_lead_status(
                lead_id=lead_id,
                status=status_val,
                gmail_draft_id=draft_id if success else None,
                conn=conn,
            )
            drafted += 1

        processed += 1

    return {
        "processed": processed,
        "drafted": drafted,
        "sent": sent,
        "parked_hitl": parked_hitl,
        "skipped_dual_attack": skipped_dual_attack,
        "mode": mode,
    }


def get_pending_outreach_leads(limit: int = 50, conn: sqlite3.Connection | None = None) -> list[dict]:
    """Retrieve all leads that have generated email drafts awaiting admin review."""
    if conn is None:
        conn = get_connection()
    rows = conn.execute(
        """
        SELECT lead_id, company_name, company_domain, role_title, contact_name,
               contact_email, email_draft_subject, email_draft_body, outreach_status,
               execution_route, created_at
        FROM recruiter_leads
        WHERE outreach_status IN ('pending_review', 'drafted', 'queued')
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def approve_outreach_lead(lead_id: str, approved_by: str = "admin", conn: sqlite3.Connection | None = None) -> bool:
    """Approve a drafted outreach email for dispatch (matches exact or prefix ID)."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        """
        UPDATE recruiter_leads
        SET outreach_status = 'approved', approved_at = ?, approved_by = ?
        WHERE lead_id = ? OR lead_id LIKE (? || '%')
        """,
        (now, approved_by, lead_id, lead_id),
    )
    conn.commit()
    matched = cursor.rowcount > 0
    if should_close:
        conn.close()
    return matched


def reject_outreach_lead(lead_id: str, reason: str = "rejected_by_admin", conn: sqlite3.Connection | None = None) -> bool:
    """Reject and cancel a drafted outreach email (matches exact or prefix ID)."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True
    cursor = conn.execute(
        """
        UPDATE recruiter_leads
        SET outreach_status = 'rejected', evidence_snippet = COALESCE(evidence_snippet, '') || ' [Admin Rejected]'
        WHERE lead_id = ? OR lead_id LIKE (? || '%')
        """,
        (lead_id, lead_id),
    )
    conn.commit()
    matched = cursor.rowcount > 0
    if should_close:
        conn.close()
    return matched


def dispatch_approved_leads(limit: int = 10, conn: sqlite3.Connection | None = None) -> dict[str, int]:
    """Send ONLY admin-approved outreach emails via Gmail API or SMTP."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    approved_rows = conn.execute(
        """
        SELECT lead_id, contact_email, company_name, role_title, email_draft_subject, email_draft_body
        FROM recruiter_leads
        WHERE outreach_status = 'approved'
        ORDER BY approved_at ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    sent = 0
    errors = 0
    for r in approved_rows:
        lead_id = r["lead_id"]
        to_email = r["contact_email"]
        subject = r["email_draft_subject"] or f"Software Engineering - {r['company_name']}"
        body = r["email_draft_body"] or ""

        success, msg_id, th_id = send_gmail_api(
            to_email=to_email,
            subject=subject,
            text_body=body,
            html_body=f"<pre style='font-family: sans-serif; white-space: pre-wrap;'>{body}</pre>",
        )
        if success:
            conn.execute(
                "UPDATE recruiter_leads SET outreach_status = 'sent', gmail_thread_id = ? WHERE lead_id = ?",
                (th_id, lead_id),
            )
            sent += 1
        else:
            conn.execute(
                "UPDATE recruiter_leads SET outreach_status = 'error_sending' WHERE lead_id = ?",
                (lead_id,),
            )
            errors += 1
        conn.commit()

    if should_close:
        conn.close()

    return {"approved_found": len(approved_rows), "sent": sent, "errors": errors}
