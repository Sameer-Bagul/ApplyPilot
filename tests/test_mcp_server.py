"""Unit tests for the ApplyPilot FastMCP server tools."""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from applypilot.database import (
    init_db,
    current_state,
    get_selectors_for_domain,
    get_hitl_ticket,
)
from applypilot.mcp_server import (
    discover_and_score_jobs,
    resolve_form_fields,
    record_learned_mapping,
    escalate_to_email_hitl,
    sync_email_hitl_replies,
    fetch_ats_otp_code,
    set_db_connection,
)


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_mcp.db"
    conn = init_db(db_file)
    return conn


@pytest.fixture(autouse=True)
def setup_mcp_test(test_db, monkeypatch):
    set_db_connection(test_db)
    monkeypatch.setattr("applypilot.hitl.email_notifier.get_connection", lambda: test_db)
    monkeypatch.setattr("applypilot.hitl.email_reply_parser.get_connection", lambda: test_db)
    yield
    set_db_connection(None)


def test_discover_and_score_jobs(test_db):
    test_db.execute(
        "INSERT INTO jobs (url, title, company, fit_score, state) VALUES (?, ?, ?, ?, 'ready_to_apply')",
        ("https://boards.greenhouse.io/acme/jobs/1", "Backend Engineer", "Acme", 9),
    )
    test_db.execute(
        "INSERT INTO jobs (url, title, company, fit_score, state) VALUES (?, ?, ?, ?, 'scored')",
        ("https://jobs.lever.co/beta/2", "Frontend Engineer", "Beta", 8),
    )
    test_db.execute(
        "INSERT INTO jobs (url, title, company, fit_score, state) VALUES (?, ?, ?, ?, 'scored')",
        ("https://example.com/low", "Intern", "Gamma", 4),
    )
    test_db.commit()

    jobs = discover_and_score_jobs(min_score=7, max_results=10)
    assert len(jobs) == 2
    urls = {j["url"] for j in jobs}
    assert "https://boards.greenhouse.io/acme/jobs/1" in urls
    assert "https://jobs.lever.co/beta/2" in urls
    assert jobs[0]["ats_type"] in {"greenhouse", "lever"}


def test_resolve_form_fields_zero_token(test_db, monkeypatch):
    # Mock candidate profile
    monkeypatch.setattr(
        "applypilot.mcp_server._load_candidate_profile",
        lambda: {
            "first_name": "Sameer",
            "last_name": "Bagul",
            "email": "sameer@example.com",
            "work_authorization": "Yes, authorized without sponsorship",
            "notice_period": "Immediate",
        },
    )

    fields = [
        {"id": "first_name", "label": "First Name", "type": "text"},
        {"id": "email", "label": "Email Address", "type": "email"},
        {
            "id": "work_auth",
            "label": "Are you legally authorized to work in the US?",
            "type": "select",
            "options": ["Yes, authorized without sponsorship", "No, need sponsorship"],
        },
        {
            "id": "unknown_essay",
            "label": "Describe a conflict you resolved with an engineering manager",
            "type": "textarea",
        },
    ]

    res = resolve_form_fields(
        ats_type="greenhouse",
        url="https://job-boards.greenhouse.io/acme/jobs/123",
        fields=fields,
    )

    assert len(res["resolved_fields"]) == 3
    assert len(res["unresolved_fields"]) == 1
    assert res["unresolved_fields"][0]["id"] == "unknown_essay"
    assert res["token_savings_pct"] == 75.0

    resolved_map = {f["field_id"]: f["value"] for f in res["resolved_fields"]}
    assert resolved_map["first_name"] == "Sameer"
    assert resolved_map["email"] == "sameer@example.com"
    assert resolved_map["work_auth"] == "Yes, authorized without sponsorship"


def test_record_learned_mapping(test_db):
    res = record_learned_mapping(
        ats_type="workday",
        url_pattern="*.myworkdayjobs.com",
        selector="input#wd_candidate_first_name",
        label="First Name",
        profile_or_qa_key="profile.first_name",
    )
    assert res["status"] == "cached"
    assert res["selector_id"] > 0

    selectors = get_selectors_for_domain("workday", "acme.myworkdayjobs.com", conn=test_db)
    assert any(s["css_or_aria_selector"] == "input#wd_candidate_first_name" for s in selectors)


def test_escalate_to_email_hitl_mcp_tool(test_db):
    url = "https://boards.greenhouse.io/acme/jobs/777"
    test_db.execute("INSERT INTO jobs (url, title, state) VALUES (?, ?, 'applying')", (url, "AI Researcher"))
    test_db.commit()

    unanswered = [
        {"field_id": "q1", "label": "Security Clearance", "type": "select", "options": ["Yes", "No"]},
    ]

    res = escalate_to_email_hitl(
        job_url=url,
        unanswered_questions=unanswered,
        reason="Novel clearance question",
    )
    assert res["ticket_id"] > 0
    assert res["job_status"] == "parked_awaiting_email"
    assert current_state(test_db, url) == "parked_awaiting_email"


def test_sync_email_hitl_replies_mcp_tool(monkeypatch):
    monkeypatch.setattr(
        "applypilot.mcp_server._sync_hitl",
        lambda poll_window_hours, conn: {"checked_threads": 2, "resolved_tickets": 1, "requeued_jobs": ["https://example.com/job1"]},
    )
    res = sync_email_hitl_replies(poll_window_hours=24)
    assert res["resolved_tickets"] == 1
    assert "https://example.com/job1" in res["requeued_jobs"]


def test_fetch_ats_otp_code_mcp_tool(monkeypatch):
    monkeypatch.setattr(
        "applypilot.mcp_server._fetch_otp",
        lambda company_domain, sender_hint, max_wait_seconds: {"otp_code": "849201", "magic_link": None},
    )
    res = fetch_ats_otp_code(company_domain="workday.com", sender_hint="Workday", wait_seconds=10)
    assert res["otp_code"] == "849201"

