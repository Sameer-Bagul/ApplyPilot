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
