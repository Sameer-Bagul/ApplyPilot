"""Unit tests for Phase 6: FastMCP Server Tools and Daily Autonomous Pipeline."""

import pytest
from applypilot.database import init_db
from applypilot.daily_runner import run_daily_pipeline
from applypilot.mcp_server import (
    discover_all_channels,
    execute_hr_outreach,
    execute_portal_applications,
    query_candidate_memory,
    resolve_company_career_portal,
    run_post_execution_learner,
    score_and_tailor_queue,
    set_db_connection,
    sync_email_replies_and_unpark,
    trigger_email_hitl,
)


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_phase6.db"
    conn = init_db(db_file)
    set_db_connection(conn)
    yield conn
    set_db_connection(None)


def test_mcp_query_candidate_memory(test_db, monkeypatch):
    monkeypatch.setattr(
        "applypilot.mcp_server._load_candidate_profile",
        lambda: {"name": "Test Engineer", "email": "engineer@test.com", "authorized_in_us": True},
    )

    res = query_candidate_memory(question_text="Email address")
    assert res["resolved_answer"] == "engineer@test.com"
    assert res["confidence"] == 1.0


def test_mcp_trigger_email_hitl(test_db):
    res = trigger_email_hitl(
        job_id="test_job_1",
        unknown_questions=[{"field_id": "q1", "label": "Preferred IDE?"}],
    )
    assert res["status"] == "parked_hitl"
    assert res["ticket_id"] >= 1


def test_mcp_score_and_tailor_queue(test_db):
    test_db.execute(
        "INSERT INTO jobs (url, title, company, fit_score, state) VALUES ('https://jobs.lever.co/test/1', 'DevOps', 'Acme', 85, 'discovered')"
    )
    test_db.commit()

    res = score_and_tailor_queue(min_score=80)
    assert len(res["eligible_jobs"]) == 1
    assert res["eligible_jobs"][0]["company"] == "Acme"


def test_mcp_discover_all_channels_empty(test_db):
    res = discover_all_channels(sources=[])
    assert res["dry_run"] is False
    assert "total_discovered" in res


def test_mcp_execute_portal_applications(test_db):
    test_db.execute(
        "INSERT INTO jobs (url, title, company, state) VALUES ('https://boards.greenhouse.io/test/2', 'SRE', 'Beta', 'ready_to_apply')"
    )
    test_db.commit()

    res = execute_portal_applications(limit=5)
    assert res["queued_portal_applications"] == 1


def test_mcp_resolve_company_career_portal(monkeypatch):
    monkeypatch.setattr(
        "applypilot.career_resolver.resolver.search_duckduckgo_html",
        lambda *args, **kwargs: [{"url": "https://boards.greenhouse.io/stripe/jobs/1", "title": "Stripe Careers", "snippet": ""}],
    )
    res = resolve_company_career_portal("Stripe")
    assert "company_name" in res
    assert res["company_name"] == "Stripe"
    assert "boards.greenhouse.io" in (res.get("resolved_ats_url") or "")


def test_run_daily_pipeline_dry_run(test_db):
    report = run_daily_pipeline(dry_run=True, sources=[], conn=test_db)
    assert report["dry_run"] is True
    assert "hitl_sync" in report
    assert "discovery" in report
    assert "scoring_and_tailoring" in report
    assert "portal_applications" in report
    assert "hr_outreach" in report
    assert "learner" in report
