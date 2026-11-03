"""Unit tests for Remote & Foreign Jobs Harvester."""

import sqlite3
import pytest

from applypilot.discovery.remote_and_foreign_jobs_harvester import (
    _clean_text,
    _extract_domain_from_url,
    fetch_remoteok_jobs,
    ingest_remote_jobs_to_db,
)
from applypilot.learning.migrations import run_migrations
from applypilot.database import init_db


@pytest.fixture
def test_db(tmp_path):
    """Temporary test database."""
    db_file = tmp_path / "test_remote.db"
    init_db(db_path=db_file)
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    run_migrations(db_path=conn)
    yield conn
    conn.close()


def test_clean_text_and_extract_domain():
    """Verify HTML cleaning and domain extraction heuristics."""
    raw = "<p>We are looking for a <strong>Senior Engineer</strong> &amp; Lead</p>"
    cleaned = _clean_text(raw)
    assert cleaned == "We are looking for a Senior Engineer & Lead"

    dom = _extract_domain_from_url("https://careers.linear.app/jobs/123")
    assert dom == "careers.linear.app"

    # Aggregators should return None
    assert _extract_domain_from_url("https://remoteok.com/remote-jobs/123") is None
    assert _extract_domain_from_url("https://jobicy.com/jobs/456") is None


def test_ingest_remote_jobs_to_db(test_db):
    """Verify storing remote jobs and enrolling companies in watchlist."""
    sample_jobs = [
        {
            "title": "Senior AI Systems Engineer",
            "company": "Vellum AI",
            "location": "Remote • Worldwide",
            "url": "https://vellum.ai/careers/senior-ai",
            "site": "RemoteOK",
            "description": "Build high-scale LLM application infrastructure.",
            "tags": ["ai", "python", "remote"],
            "domain": "vellum.ai",
            "is_remote": True,
            "is_foreign": True,
        },
        {
            "title": "Founding Fullstack Engineer",
            "company": "Supabase",
            "location": "Remote • US / Europe",
            "url": "https://supabase.com/careers/founding-engineer",
            "site": "WeWorkRemotely",
            "description": "Open source Firebase alternative.",
            "tags": ["typescript", "postgres", "remote"],
            "domain": "supabase.com",
            "is_remote": True,
            "is_foreign": True,
        },
    ]

    res = ingest_remote_jobs_to_db(sample_jobs, conn=test_db)
    assert res["jobs_stored"] >= 1
    assert res["companies_enrolled"] == 2

    # Verify career_watchlist
    c1 = test_db.execute("SELECT * FROM career_watchlist WHERE company_name = 'Vellum AI'").fetchone()
    assert c1 is not None
    assert c1["official_domain"] == "vellum.ai"
    assert c1["priority_tier"] == 1
    assert c1["is_vip"] == 1

    c2 = test_db.execute("SELECT * FROM career_watchlist WHERE company_name = 'Supabase'").fetchone()
    assert c2 is not None
    assert c2["official_domain"] == "supabase.com"
