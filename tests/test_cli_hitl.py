"""Unit tests for the applypilot hitl Typer CLI subcommand suite."""

import json
import sqlite3
import pytest
from unittest.mock import patch
from typer.testing import CliRunner
from applypilot.cli import app
from applypilot.database import init_db

runner = CliRunner()


@pytest.fixture
def mock_db(tmp_path, monkeypatch):
    """Fixture to set up an isolated test SQLite DB for CLI commands."""
    db_file = tmp_path / "test_hitl_cli.db"
    conn = init_db(db_file)

    def get_test_conn(*args, **kwargs):
        c = sqlite3.connect(str(db_file))
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr("applypilot.database.get_connection", get_test_conn)
    yield conn
    conn.close()


def test_hitl_list_command(mock_db):
    """Test listing pending tickets with both CAPTCHA and missing question blockers."""
    # Insert test jobs
    mock_db.execute(
        "INSERT INTO jobs (url, title, company, state, execution_route) VALUES (?, ?, ?, ?, ?)",
        ("https://careers.uber.com/job/1", "Staff Engineer", "Uber", "hitl", "PORTAL_ONLY"),
    )
    mock_db.execute(
        "INSERT INTO jobs (url, title, company, state, execution_route) VALUES (?, ?, ?, ?, ?)",
        ("https://careers.stripe.com/job/2", "Backend Engineer", "Stripe", "hitl", "PORTAL_ONLY"),
    )
    # Insert CAPTCHA ticket
    mock_db.execute(
        """
        INSERT INTO hitl_tickets (job_url, company, role_title, blocker_type, unanswered_questions_json, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        ("https://careers.uber.com/job/1", "Uber", "Staff Engineer", "captcha", "[]", "sent"),
    )
    # Insert Missing Info ticket
    mock_db.execute(
        """
        INSERT INTO hitl_tickets (job_url, company, role_title, blocker_type, unanswered_questions_json, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
        (
            "https://careers.stripe.com/job/2",
            "Stripe",
            "Backend Engineer",
            "missing_info",
            json.dumps([{"label": "Years of Go experience", "type": "text"}]),
            "sent",
        ),
    )
    mock_db.commit()

    result = runner.invoke(app, ["hitl", "list"])
    assert result.exit_code == 0
    assert "Uber" in result.stdout
    assert "Stripe" in result.stdout
    assert "CAPTCHA" in result.stdout
    assert "Questions" in result.stdout


def test_hitl_resolve_command(mock_db):
    """Test manually resolving a ticket via CLI."""
    mock_db.execute(
        "INSERT INTO jobs (url, title, company, state) VALUES (?, ?, ?, ?)",
        ("https://example.com/job/3", "DevOps", "Acme", "hitl"),
    )
    mock_db.execute(
        "INSERT INTO hitl_tickets (job_url, company, role_title, blocker_type, unanswered_questions_json, status, created_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
        ("https://example.com/job/3", "Acme", "DevOps", "captcha", "[]", "sent"),
    )
    mock_db.commit()

    ticket_id = mock_db.execute("SELECT ticket_id FROM hitl_tickets WHERE company = 'Acme'").fetchone()[0]

    result = runner.invoke(app, ["hitl", "resolve", str(ticket_id)])
    assert result.exit_code == 0
    assert f"Ticket #{ticket_id} marked as resolved" in result.stdout

    row = mock_db.execute("SELECT status, resolved_at FROM hitl_tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
    assert row[0] == "resolved"
    assert row[1] is not None


def test_hitl_solve_captchas_command(mock_db):
    """Test collaborative CAPTCHA blitz loop in headed mode."""
    mock_db.execute(
        "INSERT INTO jobs (url, title, company, state) VALUES (?, ?, ?, ?)",
        ("https://example.com/job/captcha-test", "Security Engineer", "Cloudflare", "hitl"),
    )
    mock_db.execute(
        "INSERT INTO hitl_tickets (job_url, company, role_title, blocker_type, unanswered_questions_json, status, created_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
        ("https://example.com/job/captcha-test", "Cloudflare", "Security Engineer", "captcha", "[]", "sent"),
    )
    mock_db.commit()

    with patch("applypilot.apply.playwright_engine.run_playwright_tier_engine", return_value=("applied", 1200, [])) as mock_run, \
         patch("applypilot.hitl.audio.play_hitl_notification_sound") as mock_sound, \
         patch("applypilot.hitl.audio.play_hitl_success_sound") as mock_success:

        result = runner.invoke(app, ["hitl", "solve-captchas"])
        assert result.exit_code == 0
        assert "Starting Collaborative CAPTCHA Blitz" in result.stdout
        assert "Application submitted and Ticket" in result.stdout
        assert "Cloudflare" in result.stdout

        mock_sound.assert_called()
        mock_success.assert_called()
        mock_run.assert_called_once()
        # Verify it was invoked with headless=False
        assert mock_run.call_args.kwargs.get("headless") is False

    # Check DB state
    ticket = mock_db.execute("SELECT status FROM hitl_tickets WHERE company = 'Cloudflare'").fetchone()
    assert ticket[0] == "resolved"

    job = mock_db.execute("SELECT state FROM jobs WHERE company = 'Cloudflare'").fetchone()
    assert job[0] == "applied"


def test_hitl_solve_missing_command_and_qa_learn(mock_db):
    """Test answering missing screening questions in CLI and auto-learning into qa_knowledge."""
    mock_db.execute(
        "INSERT INTO jobs (url, title, company, state) VALUES (?, ?, ?, ?)",
        ("https://example.com/job/qa-test", "Platform Engineer", "Datadog", "hitl"),
    )
    questions = [
        {"label": "Are you comfortable working on-call rotation?", "type": "radio", "options": ["Yes", "No"]}
    ]
    mock_db.execute(
        "INSERT INTO hitl_tickets (job_url, company, role_title, blocker_type, unanswered_questions_json, status, created_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
        ("https://example.com/job/qa-test", "Datadog", "Platform Engineer", "missing_info", json.dumps(questions), "sent"),
    )
    mock_db.commit()

    ticket_id = mock_db.execute("SELECT ticket_id FROM hitl_tickets WHERE company = 'Datadog'").fetchone()[0]

    # Provide answer "Yes" to prompt, and "n" to prompt for applying right now
    result = runner.invoke(app, ["hitl", "solve-missing", "--ticket-id", str(ticket_id)], input="Yes\nN\n")
    assert result.exit_code == 0
    assert "Saved to QA Knowledge Base" in result.stdout
    assert f"Ticket #{ticket_id} resolved" in result.stdout

    # Verify ticket resolved
    ticket_row = mock_db.execute("SELECT status FROM hitl_tickets WHERE ticket_id = ?", (ticket_id,)).fetchone()
    assert ticket_row[0] == "resolved"

    # Verify qa_knowledge contains learned answer
    qa_row = mock_db.execute("SELECT answer_text, answer_source FROM qa_knowledge WHERE question_text LIKE '%on-call%'").fetchone()
    assert qa_row is not None
    assert qa_row[0] == "Yes"
    assert qa_row[1] == "human"
