"""Unit tests for Phase 1 database migrations, FTS5 virtual table, and CRUD helpers."""

import sqlite3
import pytest
from applypilot.database import (
    init_db,
    store_recruiter_lead,
    get_recruiter_leads,
    update_recruiter_lead_status,
    upsert_career_watchlist,
    get_career_watchlist,
)
from applypilot.learning.migrations import run_migrations


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_migrations.db"
    conn = init_db(db_file)
    return conn, db_file


def test_migrations_create_all_tables_and_fts(test_db):
    conn, _ = test_db
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
        ).fetchall()
    }
    required = {
        "ats_selector_cache",
        "hitl_tickets",
        "ats_session_vault",
        "pattern_rules",
        "recruiter_leads",
        "career_watchlist",
        "qa_fts",
    }
    assert required.issubset(tables)


def test_recruiter_leads_crud(test_db):
    conn, _ = test_db
    lead_id = store_recruiter_lead(
        contact_email="recruiter@example.com",
        role_title="Senior Python Engineer",
        company_name="TechCorp",
        company_domain="techcorp.com",
        source_platform="reddit",
        source_post_url="https://reddit.com/r/forhire/123",
        evidence_snippet="Looking for a Python dev. Send resume to recruiter@example.com",
        execution_route="EMAIL_ONLY",
        conn=conn,
    )
    assert lead_id.startswith("lead_")

    leads = get_recruiter_leads(status="queued", conn=conn)
    assert len(leads) >= 1
    found = next(lead for lead in leads if lead["contact_email"] == "recruiter@example.com")
    assert found["company_name"] == "TechCorp"
    assert found["execution_route"] == "EMAIL_ONLY"

    # Update status
    updated = update_recruiter_lead_status(
        lead_id=lead_id,
        status="sent",
        gmail_draft_id="draft_123",
        conn=conn,
    )
    assert updated is True

    leads_sent = get_recruiter_leads(status="sent", conn=conn)
    assert any(lead["lead_id"] == lead_id for lead in leads_sent)


def test_career_watchlist_crud(test_db):
    conn, _ = test_db
    comp_id = upsert_career_watchlist(
        company_name="Acme Inc",
        official_domain="acme.com",
        careers_page_url="https://acme.com/careers",
        ats_provider="greenhouse",
        ats_board_token="acme",
        conn=conn,
    )
    assert comp_id.startswith("comp_")

    watchlist = get_career_watchlist(conn=conn)
    assert len(watchlist) >= 1
    item = next(w for w in watchlist if w["company_name"] == "Acme Inc")
    assert item["ats_provider"] == "greenhouse"
    assert item["ats_board_token"] == "acme"


def test_qa_fts_lexical_lookup(test_db):
    conn, _ = test_db
    conn.execute(
        "INSERT INTO qa_fts (rowid, question_key, canonical_question, question_text, answer_text) "
        "VALUES (1, 'sponsorship_required', 'Do you require visa sponsorship?', 'Will you now or in the future require sponsorship?', 'No, I am authorized to work permanently.')"
    )
    conn.commit()

    rows = conn.execute(
        "SELECT * FROM qa_fts WHERE qa_fts MATCH 'sponsorship'"
    ).fetchall()
    assert len(rows) == 1
    assert "sponsorship_required" in rows[0]["question_key"]
