import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from applypilot.database import (
    init_db,
    transition_state,
    current_state,
    create_hitl_ticket,
    resolve_hitl_ticket,
)
from applypilot.apply.playwright_engine import (
    run_playwright_tier_engine,
    _async_run_playwright_tier_engine,
)


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_engine.db"
    conn = init_db(db_file)
    return conn


def test_fallback_when_cdp_fails(test_db):
    job = {
        "url": "https://boards.greenhouse.io/acme/jobs/123",
        "title": "Software Engineer",
        "company": "Acme",
        "fit_score": 8,
    }
    # With port 99999 where no browser runs, it must gracefully fallback
    status, duration, qs = run_playwright_tier_engine(
        job=job,
        port=99999,
        worker_id=0,
        dry_run=True,
        conn=test_db,
    )
    assert status == "fallback_to_agent"
    assert qs == []


def test_playwright_engine_unresolved_screening_parks_job(test_db, monkeypatch):
    async def _run():
        job_url = "https://boards.greenhouse.io/acme/jobs/555"
        test_db.execute(
            "INSERT INTO jobs (url, title, company, fit_score, state) VALUES (?, ?, ?, ?, 'applying')",
            (job_url, "Backend Engineer", "Acme", 9),
        )
        test_db.commit()

        monkeypatch.setattr(
            "applypilot.apply.playwright_engine._load_candidate_profile",
            lambda: {"first_name": "Sameer", "last_name": "Bagul", "email": "sameer@example.com"},
        )

        mock_fill_result = {
            "filled": {"profile.first_name": "Sameer"},
            "unresolved": [
                {
                    "field_id": "security_clearance",
                    "label": "Do you hold an active Top Secret clearance?",
                    "field_type": "select",
                    "options": ["Yes", "No"],
                    "required": True,
                }
            ],
            "duration_ms": 350,
        }

        mock_page = MagicMock()
        mock_page.url = job_url
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()

        mock_context = MagicMock()
        mock_context.pages = [mock_page]
        mock_context.cookies = AsyncMock(return_value=[])
        mock_context.add_cookies = AsyncMock()

        mock_browser = MagicMock()
        mock_browser.contexts = [mock_context]

        mock_playwright = MagicMock()
        mock_playwright.chromium.connect_over_cdp = AsyncMock(return_value=mock_browser)

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_playwright
        mock_cm.__aexit__.return_value = None

        mock_pw_mod = MagicMock()
        mock_pw_async = MagicMock()
        mock_pw_mod.async_api = mock_pw_async
        mock_pw_async.async_playwright = lambda: mock_cm
        monkeypatch.setitem(sys.modules, "playwright", mock_pw_mod)
        monkeypatch.setitem(sys.modules, "playwright.async_api", mock_pw_async)

        monkeypatch.setattr(
            "applypilot.apply.playwright_engine.fill_standard_fields_playwright",
            AsyncMock(return_value=mock_fill_result),
        )
        monkeypatch.setattr(
            "applypilot.apply.playwright_engine.serialize_form_checkpoint",
            lambda page_url, step_index, filled_fields, unresolved_questions, extra_state=None: {"form_values": {"first_name": "Sameer"}},
        )
        monkeypatch.setattr(
            "applypilot.apply.playwright_engine.dispatch_hitl_email_and_park",
            lambda job, unanswered_questions, dom_checkpoint, conn: 42,
        )

        status, duration, qs = await _async_run_playwright_tier_engine(
            job={"url": job_url, "title": "Backend Engineer"},
            port=9222,
            worker_id=0,
            dry_run=False,
            conn=test_db,
        )

        assert status == "parked_awaiting_email"
        assert len(qs) == 1
        assert qs[0]["field_id"] == "security_clearance"

    asyncio.run(_run())


def test_playwright_engine_resolved_submits(test_db, monkeypatch):
    async def _run():
        job_url = "https://boards.greenhouse.io/acme/jobs/888"
        test_db.execute(
            "INSERT INTO jobs (url, title, company, fit_score, state) VALUES (?, ?, ?, ?, 'applying')",
            (job_url, "Fullstack Engineer", "Acme", 9),
        )
        test_db.commit()

        monkeypatch.setattr(
            "applypilot.apply.playwright_engine._load_candidate_profile",
            lambda: {"first_name": "Sameer", "last_name": "Bagul", "email": "sameer@example.com"},
        )

        mock_fill_result = {
            "filled": {"profile.first_name": "Sameer", "profile.email": "sameer@example.com"},
            "unresolved": [],
            "duration_ms": 400,
        }

        mock_submit_btn = MagicMock()
        mock_submit_btn.is_visible = AsyncMock(return_value=True)
        mock_submit_btn.click = AsyncMock()

        mock_page = MagicMock()
        mock_page.url = job_url
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.locator = MagicMock(return_value=MagicMock(first=mock_submit_btn))

        mock_context = MagicMock()
        mock_context.pages = [mock_page]
        mock_context.cookies = AsyncMock(return_value=[])
        mock_context.add_cookies = AsyncMock()

        mock_browser = MagicMock()
        mock_browser.contexts = [mock_context]

        mock_playwright = MagicMock()
        mock_playwright.chromium.connect_over_cdp = AsyncMock(return_value=mock_browser)

        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_playwright
        mock_cm.__aexit__.return_value = None

        mock_pw_mod = MagicMock()
        mock_pw_async = MagicMock()
        mock_pw_mod.async_api = mock_pw_async
        mock_pw_async.async_playwright = lambda: mock_cm
        monkeypatch.setitem(sys.modules, "playwright", mock_pw_mod)
        monkeypatch.setitem(sys.modules, "playwright.async_api", mock_pw_async)

        monkeypatch.setattr(
            "applypilot.apply.playwright_engine.fill_standard_fields_playwright",
            AsyncMock(return_value=mock_fill_result),
        )

        status, duration, qs = await _async_run_playwright_tier_engine(
            job={"url": job_url, "title": "Fullstack Engineer"},
            port=9222,
            worker_id=0,
            dry_run=False,
            conn=test_db,
        )

        assert status == "applied"
        assert qs == []
        mock_submit_btn.click.assert_awaited_once()

    asyncio.run(_run())
