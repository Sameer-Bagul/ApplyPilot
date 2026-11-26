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


def test_playwright_engine_records_proof_and_updates_db(test_db, monkeypatch, tmp_path):
    async def _run():
        job_url = "https://boards.greenhouse.io/acme/jobs/999"
        test_db.execute(
            "INSERT INTO jobs (url, title, company, fit_score, state) VALUES (?, ?, ?, ?, 'ready')",
            (job_url, "AI Engineer", "Acme Corp", 10),
        )
        test_db.commit()

        # Set proofs dir to tmp_path
        monkeypatch.setattr("applypilot.config.PROOFS_VIDEOS_DIR", tmp_path / "videos")
        monkeypatch.setattr("applypilot.config.PROOFS_SCREENSHOTS_DIR", tmp_path / "screenshots")

        # Create dummy source video file
        raw_video = tmp_path / "raw_test_recording.webm"
        raw_video.write_bytes(b"RIFF....WEBM_TEST_DATA")

        mock_video = MagicMock()
        mock_video.path = AsyncMock(return_value=str(raw_video))

        mock_page = MagicMock()
        mock_page.url = job_url
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.is_closed = MagicMock(return_value=False)
        mock_page.screenshot = AsyncMock()
        mock_page.close = AsyncMock()
        mock_page.video = mock_video

        mock_context = MagicMock()
        mock_context.pages = [mock_page]
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.cookies = AsyncMock(return_value=[])
        mock_context.close = AsyncMock()

        mock_browser = MagicMock()
        mock_browser.contexts = [mock_context]
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_playwright = MagicMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

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
            AsyncMock(return_value={"filled": {}, "unresolved": [], "duration_ms": 200}),
        )

        mock_submit = MagicMock()
        mock_submit.is_visible = AsyncMock(return_value=True)
        mock_submit.scroll_into_view_if_needed = AsyncMock()
        mock_submit.click = AsyncMock()
        mock_page.locator = MagicMock(return_value=MagicMock(first=mock_submit))

        # Run direct launch with auto_submit=True
        status, duration, qs = await _async_run_playwright_tier_engine(
            job={"url": job_url, "title": "AI Engineer", "company": "Acme Corp"},
            port=0,
            headless=True,
            auto_submit=True,
            conn=test_db,
        )

        assert status == "applied"
        mock_submit.click.assert_awaited_once()

        # Check DB was updated with proof paths
        row = test_db.execute("SELECT proof_video_path, proof_screenshot_path FROM jobs WHERE url = ?", (job_url,)).fetchone()
        assert row is not None
        v_path, s_path = row[0], row[1]
        assert v_path is not None
        assert "Acme_Corp" in v_path
        assert v_path.endswith(".webm")
        assert Path(v_path).exists()
        assert Path(v_path).read_bytes() == b"RIFF....WEBM_TEST_DATA"

    asyncio.run(_run())


def test_playwright_engine_captcha_triggers_flagged_captcha(test_db, monkeypatch):
    """Verify that when post-submit challenge appears, engine halts and returns flagged_captcha."""
    async def _run():
        job_url = "https://jobs.lever.co/btse/12345"
        test_db.execute(
            "INSERT INTO jobs (url, title, company, fit_score, state) VALUES (?, ?, ?, ?, 'applying')",
            (job_url, "QA Engineer", "BTSE", 9),
        )
        test_db.commit()

        mock_page = MagicMock()
        mock_page.url = job_url
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.is_closed = MagicMock(return_value=False)
        mock_page.close = AsyncMock()

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
        monkeypatch.setitem(sys.modules, "playwright", mock_pw_mod)
        monkeypatch.setitem(sys.modules, "playwright.async_api", mock_pw_async)

        monkeypatch.setattr(
            "applypilot.apply.playwright_engine.fill_standard_fields_playwright",
            AsyncMock(return_value={"filled": {"profile.first_name": "Sameer"}, "unresolved": [], "duration_ms": 200}),
        )

        mock_submit = MagicMock()
        mock_submit.is_visible = AsyncMock(return_value=True)
        mock_submit.click = AsyncMock()
        mock_page.locator = MagicMock(return_value=MagicMock(first=mock_submit))

        # Mock detect_challenge returning hCaptcha challenge post-submit
        monkeypatch.setattr(
            "applypilot.apply.playwright_engine.detect_challenge",
            AsyncMock(return_value={
                "type": "hcaptcha",
                "name": "hCaptcha Security Challenge",
                "detail": "Please click on the TWO icons that are different from the others",
            }),
        )

        status, duration, qs = await _async_run_playwright_tier_engine(
            job={"url": job_url, "title": "QA Engineer", "company": "BTSE"},
            port=9222,
            worker_id=0,
            headless=True,
            auto_submit=True,
            conn=test_db,
        )

        assert status == "flagged_captcha"
        # Verify HITL ticket was created
        ticket = test_db.execute("SELECT blocker_type, company, job_url FROM hitl_tickets WHERE job_url = ?", (job_url,)).fetchone()
        assert ticket is not None
        assert ticket[0] == "captcha"
        assert ticket[1] == "BTSE"

    asyncio.run(_run())


def test_three_stage_snapshots_captured(test_db, monkeypatch, tmp_path):
    """Verify that 01_before_fill, 02_after_feed, and 03_after_submission are captured."""
    async def _run():
        job_url = "https://boards.greenhouse.io/acme/jobs/111"
        test_db.execute(
            "INSERT INTO jobs (url, title, company, fit_score, state) VALUES (?, ?, ?, ?, 'ready')",
            (job_url, "Full Stack Engineer", "Acme", 9),
        )
        test_db.commit()

        monkeypatch.setattr("applypilot.config.PROOFS_SCREENSHOTS_DIR", tmp_path / "screenshots")
        monkeypatch.setattr("applypilot.config.PROOFS_VIDEOS_DIR", tmp_path / "videos")

        mock_page = MagicMock()
        mock_page.url = job_url
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.is_closed = MagicMock(return_value=False)
        mock_page.close = AsyncMock()
        mock_page.screenshot = AsyncMock()

        mock_context = MagicMock()
        mock_context.pages = [mock_page]
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.cookies = AsyncMock(return_value=[])
        mock_context.close = AsyncMock()

        mock_browser = MagicMock()
        mock_browser.contexts = [mock_context]
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_playwright = MagicMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

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
            AsyncMock(return_value={"filled": {"profile.email": "test@example.com"}, "unresolved": [], "duration_ms": 150}),
        )

        mock_submit = MagicMock()
        mock_submit.is_visible = AsyncMock(return_value=True)
        mock_submit.scroll_into_view_if_needed = AsyncMock()
        mock_submit.click = AsyncMock()
        mock_page.locator = MagicMock(return_value=MagicMock(first=mock_submit))

        # Mock evaluate returning confirmation text
        mock_page.evaluate = AsyncMock(return_value="Thank you for applying to Acme! Your application has been received.")

        status, duration, qs = await _async_run_playwright_tier_engine(
            job={"url": job_url, "title": "Full Stack Engineer", "company": "Acme"},
            port=0,
            headless=True,
            auto_submit=True,
            conn=test_db,
        )

        assert status == "applied"
        # Verify all 3 stage snapshots were requested
        screenshot_calls = mock_page.screenshot.call_args_list
        called_paths = [str(c[1].get("path", "")) for c in screenshot_calls]
        assert any("01_before_fill" in p for p in called_paths), "Missing 01_before_fill snapshot"
        assert any("02_after_feed" in p for p in called_paths), "Missing 02_after_feed snapshot"
        assert any("03_after_submission" in p for p in called_paths), "Missing 03_after_submission snapshot"

    asyncio.run(_run())


def test_submit_without_positive_confirmation_refuses_applied(test_db, monkeypatch, tmp_path):
    """Verify that clicking submit without positive URL/DOM confirmation refuses to mark applied."""
    async def _run():
        job_url = "https://boards.greenhouse.io/acme/jobs/222"
        test_db.execute(
            "INSERT INTO jobs (url, title, company, fit_score, state) VALUES (?, ?, ?, ?, 'ready')",
            (job_url, "DevOps Engineer", "Acme", 9),
        )
        test_db.commit()

        monkeypatch.setattr("applypilot.config.PROOFS_SCREENSHOTS_DIR", tmp_path / "screenshots")
        monkeypatch.setattr("applypilot.config.PROOFS_VIDEOS_DIR", tmp_path / "videos")

        # Use non-mock or mock configured with unconfirmed text
        mock_page = MagicMock()
        mock_page.url = job_url  # URL did not change to /thanks
        mock_page._enforce_strict_confirmation = True
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.is_closed = MagicMock(return_value=False)
        mock_page.close = AsyncMock()
        mock_page.screenshot = AsyncMock()

        mock_context = MagicMock()
        mock_context.pages = [mock_page]
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.cookies = AsyncMock(return_value=[])
        mock_context.close = AsyncMock()

        mock_browser = MagicMock()
        mock_browser.contexts = [mock_context]
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_playwright = MagicMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

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
            AsyncMock(return_value={"filled": {"profile.email": "test@example.com"}, "unresolved": [], "duration_ms": 150}),
        )

        mock_submit = MagicMock()
        mock_submit.is_visible = AsyncMock(return_value=True)
        mock_submit.scroll_into_view_if_needed = AsyncMock()
        mock_submit.click = AsyncMock()

        def mock_locator_router(sel):
            if "submit" in sel:
                return MagicMock(first=mock_submit)
            m = MagicMock()
            m.first = MagicMock(is_visible=AsyncMock(return_value=False))
            return m

        mock_page.locator = MagicMock(side_effect=mock_locator_router)

        # Evaluate returns normal page content without confirmation keywords
        mock_page.evaluate = AsyncMock(return_value="Please fill in all mandatory fields before submitting.")

        with patch("applypilot.apply.playwright_engine.detect_challenge", new=AsyncMock(return_value=None)):
            status, duration, qs = await _async_run_playwright_tier_engine(
                job={"url": job_url, "title": "DevOps Engineer", "company": "Acme"},
                port=0,
                headless=True,
                auto_submit=True,
                conn=test_db,
            )

            # Strict verification: unconfirmed submit MUST refuse applied and fallback to agent
            assert status == "fallback_to_agent"
            assert any(q["field_id"] == "unconfirmed_submit" for q in qs)
            mock_submit.click.assert_awaited_once()

    asyncio.run(_run())


def test_auto_verify_mode_unconfirmed_sets_submission_unconfirmed_in_db(test_db, monkeypatch, tmp_path):
    """When mode='auto_verify' is explicit and confirmation fails, returns 'submission_unconfirmed'."""
    async def _run():
        job_url = "https://boards.greenhouse.io/acme/jobs/999"
        test_db.execute(
            "INSERT INTO jobs (url, title, company, fit_score, state) VALUES (?, ?, ?, ?, 'ready')",
            (job_url, "Fullstack Engineer", "Acme", 8),
        )
        test_db.commit()

        monkeypatch.setattr("applypilot.config.PROOFS_SCREENSHOTS_DIR", tmp_path / "screenshots")
        monkeypatch.setattr("applypilot.config.PROOFS_VIDEOS_DIR", tmp_path / "videos")

        mock_page = MagicMock()
        mock_page.url = job_url
        mock_page._enforce_strict_confirmation = True
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.is_closed = MagicMock(return_value=False)
        mock_page.close = AsyncMock()
        mock_page.screenshot = AsyncMock()

        mock_context = MagicMock()
        mock_context.pages = [mock_page]
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.cookies = AsyncMock(return_value=[])
        mock_context.close = AsyncMock()

        mock_browser = MagicMock()
        mock_browser.contexts = [mock_context]
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_playwright = MagicMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

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
            AsyncMock(return_value={"filled": {"profile.email": "test@example.com"}, "unresolved": [], "duration_ms": 150}),
        )

        mock_submit = MagicMock()
        mock_submit.is_visible = AsyncMock(return_value=True)
        mock_submit.scroll_into_view_if_needed = AsyncMock()
        mock_submit.click = AsyncMock()

        def mock_locator_router(sel):
            if "submit" in sel:
                return MagicMock(first=mock_submit)
            m = MagicMock()
            m.first = MagicMock(is_visible=AsyncMock(return_value=False))
            return m

        mock_page.locator = MagicMock(side_effect=mock_locator_router)
        mock_page.evaluate = AsyncMock(return_value="Some error occurred or form still open.")

        with patch("applypilot.apply.playwright_engine.detect_challenge", new=AsyncMock(return_value=None)):
            status, duration, qs = await _async_run_playwright_tier_engine(
                job={"url": job_url, "title": "Fullstack Engineer", "company": "Acme"},
                port=0,
                headless=True,
                auto_submit=True,
                mode="auto_verify",
                conn=test_db,
            )

            assert status == "submission_unconfirmed"
            row = test_db.execute("SELECT state, needs_human_reason FROM jobs WHERE url = ?", (job_url,)).fetchone()
            assert row[0] == "submission_unconfirmed"
            assert row[1] == "unconfirmed_submission"

    asyncio.run(_run())


def test_revert_job_functionality(test_db):
    """Test 1-Click revert restores job from 'applied' to 'ready_to_apply'."""
    from applypilot.database import revert_job

    job_url = "https://boards.greenhouse.io/acme/jobs/revert-me"
    test_db.execute(
        "INSERT INTO jobs (url, title, company, fit_score, state, apply_status, applied_at) VALUES (?, ?, ?, ?, 'applied', 'applied', '2026-11-25T12:00:00')",
        (job_url, "Systems Engineer", "Acme", 9),
    )
    test_db.commit()

    ok = revert_job(job_url, conn=test_db)
    assert ok is True

    row = test_db.execute("SELECT state, apply_status, applied_at, needs_human_reason FROM jobs WHERE url = ?", (job_url,)).fetchone()
    assert row[0] == "ready_to_apply"
    assert row[1] == "ready"
    assert row[2] is None
    assert row[3] == "reverted_by_user_proof_inspected"


