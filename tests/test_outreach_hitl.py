"""Unit tests for Human-in-the-Loop Admin Control over Email Outreach."""

import pytest
from applypilot.database import init_db, store_recruiter_lead
from applypilot.outreach.mailer import (
    approve_outreach_lead,
    reject_outreach_lead,
    get_pending_outreach_leads,
    dispatch_approved_leads,
    run_hr_outreach,
)


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_outreach.db"
    conn = init_db(db_file)
    yield conn
    conn.close()


def test_outreach_human_in_loop_workflow(test_db):
    # 1. Store a test lead in queued status
    store_recruiter_lead(
        contact_email="recruiter@acmecorp.com",
        role_title="Backend Engineer",
        company_name="Acme Corp",
        company_domain="acmecorp.com",
        source_platform="test",
        execution_route="EMAIL_ONLY",
        conn=test_db,
    )

    lead_row = test_db.execute(
        "SELECT lead_id, outreach_status FROM recruiter_leads WHERE contact_email = 'recruiter@acmecorp.com'"
    ).fetchone()
    assert lead_row is not None
    lead_id = lead_row[0]
    assert lead_row[1] == "queued"

    # 2. Draft generation sets status to drafted / pending_review and saves subject & body
    # (Without sending anything)
    res = run_hr_outreach(mode="draft", limit=1, conn=test_db)
    assert res["drafted"] == 1
    assert res["sent"] == 0

    lead_after_draft = test_db.execute(
        "SELECT outreach_status, email_draft_subject, email_draft_body FROM recruiter_leads WHERE lead_id = ?",
        (lead_id,),
    ).fetchone()
    assert lead_after_draft[0] in ("drafted", "pending_review")
    assert lead_after_draft[1] is not None
    assert lead_after_draft[2] is not None

    # 3. get_pending_outreach_leads retrieves it
    pending = get_pending_outreach_leads(conn=test_db)
    assert any(p["lead_id"] == lead_id for p in pending)

    # 4. Attempting to dispatch before approval does NOT send it
    dispatch_res = dispatch_approved_leads(conn=test_db)
    assert dispatch_res["approved_found"] == 0
    assert dispatch_res["sent"] == 0

    # 5. Admin Approves the lead (matching full or prefix)
    approved = approve_outreach_lead(lead_id[:8], approved_by="admin_test", conn=test_db)
    assert approved is True

    row_approved = test_db.execute(
        "SELECT outreach_status, approved_by FROM recruiter_leads WHERE lead_id = ?",
        (lead_id,),
    ).fetchone()
    assert row_approved[0] == "approved"
    assert row_approved[1] == "admin_test"

    # 6. Admin can also reject a lead
    store_recruiter_lead(
        contact_email="spam@badco.com",
        role_title="Sales Rep",
        company_name="Bad Co",
        company_domain="badco.com",
        source_platform="test",
        execution_route="EMAIL_ONLY",
        conn=test_db,
    )
    bad_lead = test_db.execute(
        "SELECT lead_id FROM recruiter_leads WHERE contact_email = 'spam@badco.com'"
    ).fetchone()[0]

    rejected = reject_outreach_lead(bad_lead[:8], reason="Not relevant", conn=test_db)
    assert rejected is True

    row_rejected = test_db.execute(
        "SELECT outreach_status FROM recruiter_leads WHERE lead_id = ?",
        (bad_lead,),
    ).fetchone()
    assert row_rejected[0] == "rejected"

