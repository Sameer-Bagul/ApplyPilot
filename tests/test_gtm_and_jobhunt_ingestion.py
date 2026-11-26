"""Unit tests for GTM, Job Hunt, and LinkedIn local data ingestion pipeline."""

import csv
import sqlite3
import sys
import tempfile
from pathlib import Path

# Add project root and scripts directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pytest

from applypilot.database import get_connection, init_db
from applypilot.learning.migrations import run_migrations
from ingest_gtm_and_jobhunt_data import (
    canonicalize_domain,
    ingest_career_watchlist,
    ingest_jobs_and_history,
    ingest_linkedin_connections,
    ingest_recruiter_leads,
    ingest_screening_qa_and_sync_fts,
    is_generic_email,
    load_profile_fallbacks,
    make_synthetic_email,
    normalize_company_name,
    run_pipeline,
)


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    conn = get_connection(db_path)
    init_db(conn)
    run_migrations(conn)
    yield db_path, conn
    conn.close()
    if db_path.exists():
        db_path.unlink()


def test_normalize_company_name():
    assert normalize_company_name("Mindtickle, Inc.") == "Mindtickle"
    assert normalize_company_name("Acme Pvt. Ltd.") == "Acme"
    assert normalize_company_name("Simple Biz (Simple.biz)") == "Simple Biz"
    assert normalize_company_name("Foxelli Group") == "Foxelli Group"
    assert normalize_company_name("Company LLC.") == "Company"
    assert normalize_company_name("Test Corporation") == "Test"
    assert normalize_company_name("") == ""


def test_canonicalize_domain():
    assert canonicalize_domain("https://www.mindtickle.com/careers?ref=123") == "mindtickle.com"
    assert canonicalize_domain("http://sub.example.co.uk:8080/path#hash") == "sub.example.co.uk"
    assert canonicalize_domain("SIMPLE.BIZ/") == "simple.biz"
    assert canonicalize_domain("") == ""


def test_is_generic_email():
    assert is_generic_email("info@example.com") is True
    assert is_generic_email("sales@company.org") is True
    assert is_generic_email("support@test.io") is True
    assert is_generic_email("careers@tech.ai") is True
    assert is_generic_email("payments@theacareer.com") is True
    assert is_generic_email("operations@company.com") is True
    assert is_generic_email("john.doe@example.com") is False
    assert is_generic_email("armantas@foxelli.com") is False


def test_make_synthetic_email():
    em = make_synthetic_email("John Doe", "Acme Corp")
    assert em.startswith("linkedin-john-doe-")
    assert em.endswith("@connect.linkedin.com")


def test_load_profile_fallbacks():
    data_dir = Path("/home/sameer/Projects/ApplyPilot/data-we-can-use")
    fallbacks = load_profile_fallbacks(data_dir)
    assert fallbacks["First name"] == "Sameer"
    assert fallbacks["Last name"] == "Bagul"
    assert fallbacks["City"] == "Pune"
    assert fallbacks["Country"] == "India"
    assert "Engineering" in fallbacks["Degree"] or "Bachelor" in fallbacks["Degree"]
    assert "Pune" in fallbacks["School"]


def test_ingestion_on_temp_db(temp_db):
    db_path, conn = temp_db

    # Run ingestion with commit
    results = run_pipeline(
        db_path=db_path,
        commit=True,
    )

    # 1. Career Watchlist verification
    wl = results["career_watchlist"]
    assert wl["total_records"] > 3000
    assert wl["tier1_vip"] > 800
    assert wl["gtm_excluded"] == 623

    row = conn.execute("SELECT COUNT(*) FROM career_watchlist").fetchone()[0]
    assert row == wl["total_records"]

    # Strict check: ALL GTM excluded companies MUST have priority_tier = 2 with zero exceptions
    dnt_invalid = conn.execute(
        "SELECT COUNT(*) FROM career_watchlist WHERE stage = 'gtm_excluded' AND priority_tier != 2"
    ).fetchone()[0]
    assert dnt_invalid == 0, f"Found {dnt_invalid} Do Not Target companies with priority_tier != 2"

    # 2. Recruiter Leads verification
    ld = results["recruiter_leads"]
    assert ld["total_dms_processed"] == 816
    assert ld["total_secs_processed"] == 456
    assert ld["linkedin_only"] == 342, "All 342 decision-makers with LinkedIn URLs must be routed to LINKEDIN_ONLY"
    assert ld["total_leads_prepared"] >= 1250

    leads_count = conn.execute("SELECT COUNT(*) FROM recruiter_leads").fetchone()[0]
    assert leads_count == ld["total_leads_prepared"]

    # Verify all 342 LinkedIn decision-makers are present with correct execution route in DB
    li_count = conn.execute(
        "SELECT COUNT(*) FROM recruiter_leads WHERE execution_route = 'LINKEDIN_ONLY' AND contact_type = 'decision_maker'"
    ).fetchone()[0]
    assert li_count == 342

    # Verify inbound recruiter messages
    inbound = conn.execute(
        "SELECT contact_name, contact_email FROM recruiter_leads WHERE source_platform = 'linkedin_messages'"
    ).fetchall()
    assert len(inbound) == 5

    # 3. Jobs verification
    jb = results["jobs"]
    assert jb["curated_roles"] == 58
    assert jb["saved_roles"] == 23
    assert jb["submitted_applications"] == 108
    assert jb["total_jobs_prepared"] == 189

    jobs_count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    assert jobs_count == 189

    # Check applied jobs have state='applied' and apply_status='submitted'
    applied_count = conn.execute("SELECT COUNT(*) FROM jobs WHERE state = 'applied' AND apply_status = 'submitted'").fetchone()[0]
    assert applied_count == 108

    # 4. QA Knowledge & FTS5 verification
    qa = results["screening_qa"]
    assert qa["saved_questions"] == 83, "All 83 screening questions must be resolved and saved"
    assert qa["app_pairs_extracted"] > 500

    qa_count = conn.execute("SELECT COUNT(*) FROM qa_knowledge").fetchone()[0]
    fts_count = conn.execute("SELECT COUNT(*) FROM qa_fts").fetchone()[0]
    assert qa_count > 250
    assert qa_count == fts_count, f"qa_knowledge count ({qa_count}) must match qa_fts count ({fts_count}) exactly"

    # Verify zero orphaned FTS rows
    orphans = conn.execute("SELECT COUNT(*) FROM qa_fts WHERE rowid NOT IN (SELECT id FROM qa_knowledge)").fetchone()[0]
    assert orphans == 0, f"Found {orphans} orphaned rows in qa_fts"

    # FTS Match query verification
    fts_res = conn.execute(
        "SELECT question_text, answer_text FROM qa_fts WHERE qa_fts MATCH ?",
        ("pune",),
    ).fetchall()
    assert len(fts_res) > 0


def test_linkedin_connections_hook_normalized(temp_db):
    db_path, conn = temp_db

    # Insert a target company with legal suffix
    conn.execute(
        "INSERT INTO career_watchlist (company_id, company_name, priority_tier) VALUES (?, ?, ?)",
        ("comp_test_123", "Acme AI, Inc.", 1),
    )
    conn.commit()

    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
        writer = csv.writer(f)
        writer.writerow(["First Name", "Last Name", "URL", "Email Address", "Company", "Position", "Connected On"])
        # Connection lists "Acme AI" without legal suffix
        writer.writerow(["Alice", "Smith", "https://linkedin.com/in/alicesmith", "alice@example.com", "Acme AI", "Staff Engineer", "2026-01-01"])
        csv_path = Path(f.name)

    try:
        res = ingest_linkedin_connections(conn, connections_csv_path=csv_path, dry_run=False)
        conn.commit()
        assert res["status"] == "success"
        assert res["connections_count"] == 1
        assert res["matched_companies"] == 1

        row = conn.execute("SELECT referral_available, referrer_name, referrer_linkedin FROM career_watchlist WHERE company_id = ?", ("comp_test_123",)).fetchone()
        assert row[0] == 1
        assert row[1] == "Alice Smith"
        assert row[2] == "https://linkedin.com/in/alicesmith"
    finally:
        if csv_path.exists():
            csv_path.unlink()
