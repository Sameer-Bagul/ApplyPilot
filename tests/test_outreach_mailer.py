"""Unit tests for Phase 4: Automated HR & Founder Cold Mailer (Track A)."""

import pytest
from applypilot.database import (
    init_db,
    store_recruiter_lead,
    get_recruiter_leads,
)
from applypilot.outreach.mailer import (
    compose_cold_email,
    extract_special_instructions,
    run_hr_outreach,
)


@pytest.fixture
def db_conn(tmp_path):
    db_file = tmp_path / "test_outreach.db"
    conn = init_db(db_file)
    return conn


def test_extract_special_instructions():
    post_text = """
    Hiring Senior Python Engineer.
    Please use Subject line: [Senior Python] - [Name]
    Include your notice period and current CTC.
    """
    instr = extract_special_instructions(post_text)
    assert instr["required_subject"] == "[Senior Python] - [Name]"
    assert instr.get("needs_notice_period") is True
    assert instr.get("needs_salary") is True


def test_compose_cold_email():
    lead = {
        "role_title": "AI Backend Engineer",
        "company_name": "Novatech",
        "source_platform": "x",
        "source_post_url": "https://x.com/post/999",
        "contact_type": "founder",
    }
    profile = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "summary": "AI systems architect.",
        "github": "https://github.com/janedoe",
        "linkedin": "https://linkedin.com/in/janedoe",
    }
    special = {"required_subject": "AI Engineer Application - [Name]"}

    subject, text_body, html_body = compose_cold_email(
        lead=lead,
        profile=profile,
        special_instructions=special,
        has_submitted_portal=True,
    )

    assert subject == "AI Engineer Application - Jane Doe"
    assert "https://x.com/post/999" in text_body
    assert "official career portal" in text_body
    assert "Jane Doe" in text_body


def test_run_hr_outreach_draft_mode(db_conn):
    lead_id = store_recruiter_lead(
        contact_email="hr@novatech.io",
        role_title="Founding Engineer",
        company_name="Novatech",
        source_platform="reddit",
        source_post_url="https://reddit.com/r/forhire/101",
        evidence_snippet="Looking for a founding engineer. Email hr@novatech.io",
        execution_route="EMAIL_ONLY",
        conn=db_conn,
    )

    summary = run_hr_outreach(mode="draft", limit=5, conn=db_conn)
    assert summary["processed"] == 1
    assert summary["drafted"] == 1

    leads = get_recruiter_leads(status="drafted", conn=db_conn)
    assert any(l["lead_id"] == lead_id for l in leads)


def test_run_hr_outreach_dual_attack_skips_until_applied(db_conn):
    lead_id = store_recruiter_lead(
        contact_email="founder@dualcorp.com",
        role_title="Core Systems Developer",
        company_name="DualCorp",
        source_platform="linkedin",
        source_post_url="https://linkedin.com/posts/123",
        evidence_snippet="Apply online and email founder@dualcorp.com",
        execution_route="DUAL_ATTACK",
        conn=db_conn,
    )

    # Portal job exists but state is 'discovered' (not yet 'applied')
    db_conn.execute(
        "INSERT INTO jobs (url, company, title, state) VALUES ('https://jobs.lever.co/dualcorp/1', 'DualCorp', 'Core Systems Developer', 'discovered')"
    )
    db_conn.commit()

    summary = run_hr_outreach(mode="draft", limit=5, conn=db_conn)
    assert summary["skipped_dual_attack"] == 1
    assert summary["drafted"] == 0

    # Now mark job as applied
    db_conn.execute(
        "UPDATE jobs SET state = 'applied' WHERE company = 'DualCorp'"
    )
    db_conn.commit()

    summary2 = run_hr_outreach(mode="draft", limit=5, conn=db_conn)
    assert summary2["skipped_dual_attack"] == 0
    assert summary2["drafted"] == 1


def test_send_smtp_email_mock():
    from applypilot.outreach.mailer import send_smtp_email
    success, msg_id = send_smtp_email(
        to_email="test@example.com",
        subject="Test Subject",
        text_body="Test Body",
        html_body="<p>Test Body</p>",
    )
    assert success is True
    assert msg_id is not None
    assert "mock" in msg_id


def test_send_smtp_email_mocked_server(monkeypatch, tmp_path):
    from unittest.mock import MagicMock
    import smtplib
    from applypilot.outreach.mailer import send_smtp_email

    mock_smtp_instance = MagicMock()
    mock_smtp_class = MagicMock(return_value=mock_smtp_instance)
    mock_smtp_instance.__enter__.return_value = mock_smtp_instance

    monkeypatch.setattr(smtplib, "SMTP", mock_smtp_class)

    dummy_resume = tmp_path / "resume.pdf"
    dummy_resume.write_bytes(b"%PDF-1.4 test")

    success, msg_id = send_smtp_email(
        to_email="recruiter@tech.co",
        subject="Application for Senior Engineer",
        text_body="Hello, here is my application.",
        html_body="<p>Hello</p>",
        attachment_path=dummy_resume,
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_user="user@gmail.com",
        smtp_pass="app_password_1234",
        use_ssl=False,
    )

    assert success is True
    assert msg_id is not None
    mock_smtp_class.assert_called_once_with("smtp.gmail.com", 587, timeout=30)
    mock_smtp_instance.starttls.assert_called_once()
    mock_smtp_instance.login.assert_called_once_with("user@gmail.com", "app_password_1234")
    mock_smtp_instance.send_message.assert_called_once()


def test_send_single_lead_email(db_conn):
    from applypilot.outreach.mailer import send_single_lead_email, save_single_lead_draft
    lead_id = store_recruiter_lead(
        contact_email="ceo@stealth.ai",
        role_title="Founding AI Engineer",
        company_name="Stealth AI",
        source_platform="x",
        evidence_snippet="Looking for AI engineer",
        execution_route="EMAIL_ONLY",
        conn=db_conn,
    )

    # Save draft first
    res_draft = save_single_lead_draft(
        lead_id=lead_id,
        subject="AI Engineer Pitch — Sameer",
        body_text="Hi, I built autonomous agents...",
        conn=db_conn,
    )
    assert res_draft["success"] is True
    assert res_draft["status"] == "drafted"

    # Now send single email
    res_send = send_single_lead_email(lead_id=lead_id, conn=db_conn)
    assert res_send["success"] is True
    assert res_send["status"] == "sent"
    assert res_send["to_email"] == "ceo@stealth.ai"

    row = db_conn.execute("SELECT outreach_status, email_subject FROM recruiter_leads WHERE lead_id = ?", (lead_id,)).fetchone()
    assert row[0] == "sent"
    assert row[1] == "AI Engineer Pitch — Sameer"


def test_send_smtp_email_with_str_attachment_path(monkeypatch, tmp_path):
    """Verifies that passing attachment_path as a str (not Path object) works without error."""
    from unittest.mock import MagicMock
    import smtplib
    from applypilot.outreach.mailer import send_smtp_email

    mock_smtp_instance = MagicMock()
    mock_smtp_class = MagicMock(return_value=mock_smtp_instance)
    mock_smtp_instance.__enter__.return_value = mock_smtp_instance
    monkeypatch.setattr(smtplib, "SMTP", mock_smtp_class)

    dummy_resume = tmp_path / "resume.pdf"
    dummy_resume.write_bytes(b"%PDF-1.4 test")

    success, msg_id = send_smtp_email(
        to_email="recruiter@tech.co",
        subject="Application for Senior Engineer",
        text_body="Hello, here is my application.",
        html_body="<p>Hello</p>",
        attachment_path=str(dummy_resume),  # String path!
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_user="user@gmail.com",
        smtp_pass="app_password_1234",
        use_ssl=False,
    )

    assert success is True
    assert msg_id is not None
    mock_smtp_instance.send_message.assert_called_once()


def test_send_smtp_email_ssl_port_465(monkeypatch):
    """Verifies SSL connection when port 465 / use_ssl=True is passed."""
    from unittest.mock import MagicMock
    import smtplib
    from applypilot.outreach.mailer import send_smtp_email

    mock_ssl_instance = MagicMock()
    mock_ssl_class = MagicMock(return_value=mock_ssl_instance)
    mock_ssl_instance.__enter__.return_value = mock_ssl_instance
    monkeypatch.setattr(smtplib, "SMTP_SSL", mock_ssl_class)

    success, msg_id = send_smtp_email(
        to_email="recruiter@tech.co",
        subject="Application for Senior Engineer",
        text_body="Hello",
        html_body="<p>Hello</p>",
        smtp_host="smtp.gmail.com",
        smtp_port=465,
        smtp_user="user@gmail.com",
        smtp_pass="app_password_1234",
        use_ssl=True,
    )

    assert success is True
    mock_ssl_class.assert_called_once()
    mock_ssl_instance.login.assert_called_once_with("user@gmail.com", "app_password_1234")
    mock_smtp_instance = mock_ssl_instance
    mock_smtp_instance.send_message.assert_called_once()


def test_send_single_lead_email_personal_preferred(db_conn):
    from applypilot.outreach.mailer import send_single_lead_email
    lead_id = store_recruiter_lead(
        contact_email="corp@stealth.ai",
        role_title="Staff Engineer",
        company_name="Stealth AI",
        source_platform="x",
        conn=db_conn,
    )
    db_conn.execute(
        "UPDATE recruiter_leads SET personal_email = 'founder.personal@gmail.com', preferred_channel = 'personal' WHERE lead_id = ?",
        (lead_id,),
    )
    db_conn.commit()

    res = send_single_lead_email(lead_id=lead_id, conn=db_conn)
    assert res["success"] is True
    assert res["to_email"] == "founder.personal@gmail.com"


def test_send_single_lead_email_auto_composes_when_empty(db_conn):
    """If a lead has no draft yet, sending it auto-composes pitch from candidate profile."""
    from applypilot.outreach.mailer import send_single_lead_email
    lead_id = store_recruiter_lead(
        contact_email="cto@autotech.dev",
        role_title="Backend Lead",
        company_name="AutoTech",
        source_platform="linkedin",
        evidence_snippet="Looking for backend lead with Python and FastAPI",
        conn=db_conn,
    )

    # Lead has no email_subject or email_body_text
    res = send_single_lead_email(lead_id=lead_id, conn=db_conn)
    assert res["success"] is True
    assert res["status"] == "sent"
    assert "Backend Lead" in res["subject"]

