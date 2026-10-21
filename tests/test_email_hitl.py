"""Unit tests for the Asynchronous Email HITL system.

Covers:
- Outbound email formatting (subject, plaintext, HTML, options, suggested drafts)
- Job parking on email dispatch (parked_awaiting_email transition)
- Inbound email quote stripping and answer parsing (Q1: A, Q2: APPROVE)
- Dropdown option resolution from shorthand letters
- Full reply processing: updates QA database, resolves ticket, and requeues job (queued_resume)
- OTP code and magic link extraction
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from applypilot.database import (
    init_db,
    current_state,
    lookup_qa,
    get_hitl_ticket,
)
from applypilot.hitl.email_notifier import (
    format_hitl_email_subject,
    format_hitl_email_body,
    dispatch_hitl_email_and_park,
)
from applypilot.hitl.email_reply_parser import (
    strip_email_quoted_headers,
    parse_reply_answers,
    resolve_answer_for_question,
    process_hitl_ticket_reply,
)
from applypilot.hitl.otp_interceptor import (
    extract_otp_from_text,
    extract_magic_link_from_text,
)


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_hitl.db"
    conn = init_db(db_file)
    return conn


def test_format_hitl_email():
    job = {
        "title": "Senior AI Agent Engineer",
        "company": "Acme Robotics",
        "url": "https://boards.greenhouse.io/acme/jobs/101",
        "fit_score": 9,
    }
    questions = [
        {
            "field_id": "q1",
            "label": "Are you willing to attend quarterly sprints in San Francisco?",
            "field_type": "select",
            "required": True,
            "options": ["Yes, willing to travel", "No, 100% remote only"],
        },
        {
            "field_id": "q2",
            "label": "Describe a project where you reduced LLM token cost:",
            "field_type": "textarea",
            "required": True,
            "suggested_draft": "Built a deterministic caching layer that reduced tokens by 85%.",
        },
    ]

    subject = format_hitl_email_subject(ticket_id=1042, job=job, question_count=2)
    assert "[ApplyPilot HITL #1042]" in subject
    assert "Senior AI Agent Engineer" in subject
    assert "Acme Robotics" in subject
    assert "Score: 9/10" in subject

    text_body, html_body = format_hitl_email_body(1042, job, questions, "Step 2")
    assert "Q1 [Required | Select]" in text_body
    assert "A) Yes, willing to travel" in text_body
    assert "B) No, 100% remote only" in text_body
    assert "Q2 [Required | Textarea]" in text_body
    assert "Suggested Draft (from profile): Built a deterministic caching layer" in text_body
    assert "Q1: A" in text_body


def test_dispatch_hitl_email_and_park(test_db):
    url = "https://boards.greenhouse.io/acme/jobs/101"
    test_db.execute("INSERT INTO jobs (url, title, state) VALUES (?, ?, 'applying')", (url, "AI Engineer"))
    test_db.commit()

    job = {"url": url, "title": "AI Engineer", "company": "Acme", "fit_score": 9}
    questions = [
        {"field_id": "q1", "label": "Security Clearance", "field_type": "select", "options": ["Yes", "No"], "required": True}
    ]

    ticket_id = dispatch_hitl_email_and_park(
        job=job,
        unanswered_questions=questions,
        recipient_email="testuser@example.com",
        conn=test_db,
    )

    assert ticket_id > 0
    assert current_state(test_db, url) == "parked_awaiting_email"

    ticket = get_hitl_ticket(ticket_id, conn=test_db)
    assert ticket is not None
    assert ticket["status"] == "sent"
    assert len(ticket["unanswered_questions"]) == 1


def test_strip_email_quoted_headers():
    raw_email = """Q1: A
Q2: APPROVE

On Wed, Oct 21, 2026 at 4:00 PM ApplyPilot <agent@example.com> wrote:
> ApplyPilot HITL Escalation — Ticket #1042
> Questions requiring your input:
"""
    cleaned = strip_email_quoted_headers(raw_email)
    assert cleaned == "Q1: A\nQ2: APPROVE"


def test_parse_reply_answers():
    reply_body = """
    Q1: A
    Q2: APPROVE
    Q3 - Over 4 years deploying cloud infrastructure on AWS.
    """
    answers = parse_reply_answers(reply_body)
    assert answers[1] == "A"
    assert answers[2] == "APPROVE"
    assert answers[3] == "Over 4 years deploying cloud infrastructure on AWS."


def test_resolve_answer_for_question():
    q_dropdown = {
        "label": "Work Authorization",
        "options": ["Authorized without sponsorship", "Requires sponsorship"],
        "required": True,
    }
    # Option letter A
    val, err = resolve_answer_for_question("A", q_dropdown)
    assert err is None
    assert val == "Authorized without sponsorship"

    # Option letter B
    val, err = resolve_answer_for_question("b", q_dropdown)
    assert err is None
    assert val == "Requires sponsorship"

    # Suggested draft APPROVE
    q_text = {
        "label": "GitHub Link",
        "suggested_draft": "https://github.com/sameer",
        "required": True,
    }
    val, err = resolve_answer_for_question("APPROVE", q_text)
    assert err is None
    assert val == "https://github.com/sameer"

    # Custom text override
    val, err = resolve_answer_for_question("https://github.com/custom-profile", q_text)
    assert err is None
    assert val == "https://github.com/custom-profile"


def test_full_hitl_reply_processing_roundtrip(test_db):
    url = "https://boards.greenhouse.io/acme/jobs/202"
    test_db.execute("INSERT INTO jobs (url, title, state) VALUES (?, ?, 'applying')", (url, "Platform Engineer"))
    test_db.commit()

    job = {"url": url, "title": "Platform Engineer", "company": "Acme", "fit_score": 8}
    questions = [
        {
            "field_id": "q1",
            "label": "Notice Period",
            "field_type": "select",
            "options": ["Immediate (0-15 days)", "1 month", "2+ months"],
            "required": True,
        },
        {
            "field_id": "q2",
            "label": "Are you comfortable working with Go and Python?",
            "field_type": "text",
            "suggested_draft": "Yes, proficient in both Go microservices and Python AI systems.",
            "required": True,
        },
    ]

    ticket_id = dispatch_hitl_email_and_park(
        job=job,
        unanswered_questions=questions,
        recipient_email="user@example.com",
        conn=test_db,
    )
    assert current_state(test_db, url) == "parked_awaiting_email"

    # Simulate user sending reply from their phone
    incoming_reply = """
    Q1: A
    Q2: APPROVE

    Sent from my iPhone
    > On Oct 21 ApplyPilot wrote:
    """

    res = process_hitl_ticket_reply(ticket_id=ticket_id, reply_body=incoming_reply, conn=test_db)
    assert res["success"] is True

    # 1. Job transitioned to queued_resume
    assert current_state(test_db, url) == "queued_resume"

    # 2. Ticket resolved
    ticket = get_hitl_ticket(ticket_id, conn=test_db)
    assert ticket["status"] == "resolved"

    # 3. Facts stored permanently in qa_knowledge_base
    qa_rows = lookup_qa("Notice Period", conn=test_db)
    assert len(qa_rows) >= 1
    assert qa_rows[0]["answer_text"] == "Immediate (0-15 days)"
    assert qa_rows[0]["answer_source"] == "human_email"


def test_extract_otp_and_magic_link():
    otp_text = "Your Workday verification code is 849201. Please enter this code within 15 minutes."
    assert extract_otp_from_text(otp_text) == "849201"

    short_otp = "One-time passcode: 394812"
    assert extract_otp_from_text(short_otp) == "394812"

    magic_text = "Click here to activate your account: https://acme.myworkdayjobs.com/en-US/activate?token=abc123xyz"
    assert extract_magic_link_from_text(magic_text) == "https://acme.myworkdayjobs.com/en-US/activate?token=abc123xyz"
