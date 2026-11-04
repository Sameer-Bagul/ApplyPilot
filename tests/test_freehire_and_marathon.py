"""Unit tests for FreeHire Harvester and Marathon Continuous Pipeline Runner."""

import sqlite3
import pytest
from unittest.mock import MagicMock, patch

from applypilot.database import get_career_watchlist, init_db
from applypilot.discovery.freehire_harvester import (
    FREEHIRE_TECH_CATEGORIES,
    FreeHireClient,
    format_salary,
    harvest_freehire_domain,
    ingest_freehire_jobs,
)
from applypilot.marathon_runner import DOMAIN_ROTATION_CLUSTERS, MarathonSession


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_marathon.db"
    conn = init_db(db_file)
    yield conn
    conn.close()


def test_freehire_salary_formatting():
    assert format_salary(100000, 150000, "USD", "year") == "USD 100,000 - 150,000/year"
    assert format_salary(80000, None, "EUR", "year") == "EUR 80,000/year"
    assert format_salary(None, 60, "USD", "hour") == "USD up to 60/hour"
    assert format_salary(None, None) is None


def test_freehire_ingestion_and_deduplication(test_db):
    sample_jobs = [
        {
            "slug": "senior-ai-agent-engineer-anthropic-xyz",
            "title": "Senior AI Agent Engineer",
            "company": "Anthropic Partner",
            "location": "Remote",
            "summary": "Build state of the art autonomous LLM agentic systems with Python, LangGraph and MCP protocols.",
            "official_job_url": "https://jobs.lever.co/anthropic-partner/123",
            "source": "lever",
            "salary_min": 180000,
            "salary_max": 240000,
            "salary_currency": "USD",
            "salary_period": "year",
            "posted_at": "2026-11-04T05:00:00Z",
        },
        {
            "slug": "staff-fullstack-engineer-scale-abc",
            "title": "Staff Fullstack Engineer",
            "company": "ScaleAI Co",
            "location": "San Francisco, CA (Remote)",
            "summary": "Lead fullstack development using React, TypeScript, FastAPI, and Postgres.",
            "official_job_url": "https://boards.greenhouse.io/scaleaico/jobs/456",
            "source": "greenhouse",
            "salary_min": 200000,
            "salary_max": 270000,
            "salary_currency": "USD",
            "salary_period": "year",
            "posted_at": "2026-11-03T10:00:00Z",
        },
    ]

    stats1 = ingest_freehire_jobs(sample_jobs, conn=test_db)
    assert stats1["new"] == 2
    assert stats1["existing"] == 0
    assert stats1["companies_added"] == 2

    # Check database rows
    row = test_db.execute(
        "SELECT title, company, salary, execution_route, state FROM jobs WHERE url = ?",
        ("https://jobs.lever.co/anthropic-partner/123",),
    ).fetchone()
    assert row is not None
    assert row["title"] == "Senior AI Agent Engineer"
    assert row["company"] == "Anthropic Partner"
    assert "180,000" in row["salary"]
    assert row["execution_route"] == "PORTAL_ONLY"

    # Verify career_watchlist has newly ingested employers
    wl = get_career_watchlist(conn=test_db)
    company_names = [w["company_name"] for w in wl]
    assert "Anthropic Partner" in company_names
    assert "ScaleAI Co" in company_names

    # Run ingestion again -> should deduplicate cleanly
    stats2 = ingest_freehire_jobs(sample_jobs, conn=test_db)
    assert stats2["new"] == 0
    assert stats2["existing"] == 2


def test_harvest_freehire_domain_mock(test_db):
    mock_client = MagicMock()
    mock_client.search_jobs.return_value = {
        "jobs": [
            {
                "slug": "lead-ml-engineer-cohere-789",
                "title": "Lead ML Engineer",
                "company": "Cohere Corp",
                "location": "Remote",
                "summary": "Develop frontier embeddings and search models.",
                "official_job_url": "https://jobs.ashbyhq.com/cohere/789",
                "source": "ashby",
            }
        ],
        "total": 450,
    }

    res = harvest_freehire_domain("ai_engineering", limit=10, conn=test_db, client=mock_client)
    assert res["category"] == "ai_engineering"
    assert res["scraped"] == 1
    assert res["ingested_new"] == 1
    assert res["catalogue_total"] == 450


def test_marathon_session_time_budget():
    # 0.05 min session = 3 seconds
    session = MarathonSession(duration_minutes=0.05, continuous=False)
    assert not session.is_time_up
    assert session.remaining_seconds > 0

    # Continuous session
    cont_session = MarathonSession(duration_minutes=60.0, continuous=True)
    assert not cont_session.is_time_up
    assert cont_session.remaining_seconds == float("inf")


def test_domain_rotation_clusters_coverage():
    all_clustered_categories = []
    for cluster in DOMAIN_ROTATION_CLUSTERS:
        all_clustered_categories.extend(cluster["categories"])

    # Ensure major tech categories are covered in the rotation clusters
    for cat in ["ai_engineering", "software_engineering", "backend", "fullstack", "devops"]:
        assert cat in all_clustered_categories
        assert cat in FREEHIRE_TECH_CATEGORIES


def test_cli_marathon_and_freehire_registered():
    from applypilot.cli import app
    command_names = [cmd.name for cmd in app.registered_commands]
    assert "marathon" in command_names
    assert "harvest-freehire" in command_names


def test_dead_job_eviction_slice(test_db):
    from applypilot.marathon_runner import _run_dead_job_eviction_slice
    from applypilot.discovery.freehire_harvester import FreeHireClient

    # Insert a fake FreeHire job
    test_db.execute(
        """
        INSERT INTO jobs (url, title, company, site, strategy, state)
        VALUES ('https://freehire.me/jobs/closed-test-job-123', 'Closed Dev', 'Test Co', 'freehire/lever', 'freehire', 'enriched')
        """
    )
    test_db.commit()

    with patch.object(FreeHireClient, "check_jobs_open") as mock_check:
        mock_check.return_value = {
            "jobs": [{"slug": "closed-test-job-123", "status": "closed"}]
        }
        evicted = _run_dead_job_eviction_slice(limit=10, conn=test_db)
        assert evicted == 1

        row = test_db.execute(
            "SELECT state FROM jobs WHERE url = 'https://freehire.me/jobs/closed-test-job-123'"
        ).fetchone()
        assert row["state"] == "archived"


def test_local_matcher_score_all_retained(test_db):
    from applypilot.scoring.scorer import score_job, _flush_score_batch

    high_job = {
        "url": "https://company.com/jobs/senior-python-dev",
        "title": "Senior Python Backend Engineer",
        "full_description": "We need 5+ years of Python, FastAPI, PostgreSQL, Docker, AWS, Microservices architecture.",
        "location": "Remote",
    }
    low_job = {
        "url": "https://company.com/jobs/cashier-store",
        "title": "Bakery Cashier",
        "full_description": "Operate cash register and assist customers.",
        "location": "San Francisco",
    }

    res_high = score_job("", high_job, use_algo_only=True)
    res_high["url"] = high_job["url"]
    assert res_high["score"] >= 7

    res_low = score_job("", low_job, use_algo_only=True)
    res_low["url"] = low_job["url"]
    assert res_low["score"] <= 4

    # Insert initial rows
    test_db.execute("INSERT INTO jobs (url, title, company, state) VALUES (?, ?, ?, 'enriched')",
                    (high_job["url"], high_job["title"], "Tech Co"))
    test_db.execute("INSERT INTO jobs (url, title, company, state) VALUES (?, ?, ?, 'enriched')",
                    (low_job["url"], low_job["title"], "Bakery Co"))
    test_db.commit()

    _flush_score_batch(test_db, [res_high, res_low], "2026-11-04T12:00:00Z")

    row_h = test_db.execute("SELECT fit_score, state FROM jobs WHERE url = ?", (high_job["url"],)).fetchone()
    row_l = test_db.execute("SELECT fit_score, state FROM jobs WHERE url = ?", (low_job["url"],)).fetchone()

    assert row_h["fit_score"] >= 7
    assert row_h["state"] == "scored"
    assert row_l["fit_score"] <= 4
    assert row_l["state"] == "low_score"  # Universal preservation: retained, never dropped


