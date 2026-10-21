import os
import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

from applypilot.database import get_connection, init_db
from applypilot.hitl.otp_interceptor import extract_otp_from_text
from applypilot.hitl.email_reply_parser import parse_reply_answers
from applypilot.apply.playwright_engine import _async_run_playwright_tier_engine


def test_otp_extraction_ignores_bare_zip_codes_and_numbers():
    # Bare numbers, zip codes, and order numbers must NOT be matched as OTPs
    assert extract_otp_from_text("Shipment to postal code 94105 delivered yesterday.") is None
    assert extract_otp_from_text("Order #849201 has been confirmed.") is None
    assert extract_otp_from_text("Call us at 650-123456 for assistance.") is None

    # Contextual keywords MUST match
    assert extract_otp_from_text("Your verification code is 849201.") == "849201"
    assert extract_otp_from_text("Your security code: 123456") == "123456"
    assert extract_otp_from_text("Use one-time passcode 987654 to log in.") == "987654"
    assert extract_otp_from_text("OTP: 456789") == "456789"
    assert extract_otp_from_text("Your confirmation code is 112233.") == "112233"


def test_sqlite_foreign_keys_pragma(tmp_path):
    db_file = tmp_path / "test_fk.db"
    conn = get_connection(db_file)
    row = conn.execute("PRAGMA foreign_keys").fetchone()
    assert row[0] == 1


def test_playwright_submission_fails_on_visible_dom_errors(monkeypatch, tmp_path):
    async def _run():
        db_file = tmp_path / "test_pw_err.db"
        conn = init_db(db_file)
        job_url = "https://boards.greenhouse.io/acme/jobs/999"
        conn.execute(
            "INSERT INTO jobs (url, title, company, fit_score, state) VALUES (?, ?, ?, ?, 'applying')",
            (job_url, "SRE", "Acme", 8),
        )
        conn.commit()

        monkeypatch.setattr(
            "applypilot.apply.playwright_engine._load_candidate_profile",
            lambda: {"first_name": "Test", "last_name": "User", "email": "test@example.com"},
        )
        monkeypatch.setattr(
            "applypilot.apply.playwright_engine.fill_standard_fields_playwright",
            AsyncMock(return_value={"filled": {"first_name": "Test"}, "unresolved": [], "duration_ms": 100}),
        )

        mock_submit_btn = MagicMock()
        mock_submit_btn.is_visible = AsyncMock(return_value=True)
        mock_submit_btn.click = AsyncMock()

        mock_error_loc = MagicMock()
        mock_error_loc.is_visible = AsyncMock(return_value=True)

        def mock_locator(sel):
            mock_obj = MagicMock()
            if "submit" in sel.lower() or "apply" in sel.lower():
                mock_obj.first = mock_submit_btn
            elif "error" in sel or "invalid" in sel or "alert" in sel:
                mock_obj.first = mock_error_loc
            else:
                mock_obj.first = MagicMock(is_visible=AsyncMock(return_value=False))
            return mock_obj

        mock_page = MagicMock()
        mock_page.url = job_url
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.locator = mock_locator

        mock_context = MagicMock()
        mock_context.pages = [mock_page]
        mock_context.cookies = AsyncMock(return_value=[])

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

        monkeypatch.setitem(os.sys.modules, "playwright", mock_pw_mod)
        monkeypatch.setitem(os.sys.modules, "playwright.async_api", mock_pw_async)

        status, duration, qs = await _async_run_playwright_tier_engine(
            job={"url": job_url, "title": "SRE"},
            port=9222,
            worker_id=0,
            dry_run=False,
            conn=conn,
        )

        # When validation errors appear on the page, the status must NOT be "applied"
        assert status == "fallback_to_agent"

    import asyncio
    asyncio.run(_run())
