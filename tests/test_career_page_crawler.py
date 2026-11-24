"""Unit tests for HyprlandController and CareerPageCrawler."""

from __future__ import annotations

import asyncio
import json
import sqlite3
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from applypilot.database import init_db
from applypilot.discovery.career_page_crawler import (
    CareerPageCrawler,
    CANDIDATE_SKILLS,
    TECH_ROLES_PATTERN,
)
from applypilot.system.hyprland_controller import HyprlandController


@pytest.fixture
def test_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def test_hyprland_controller_config():
    ctl = HyprlandController(workspace=11, window_class="ApplyPilotCrawler")
    geom = ctl.get_monitor_geometry()
    assert len(geom) == 2
    assert geom[0] > 0 and geom[1] > 0

    cfg = ctl.get_playwright_launch_config(headless=False)
    assert cfg["headless"] is False
    assert any("--class=ApplyPilotCrawler" in arg for arg in cfg["args"])
    assert cfg["viewport"]["width"] == geom[0]


def test_resolve_career_url(test_db):
    crawler = CareerPageCrawler(workspace=11, conn=test_db)

    # 1. Greenhouse domain
    url, ats = crawler.resolve_career_url("Anthropic", "anthropic.greenhouse.io")
    assert "boards.greenhouse.io" in url
    assert ats == "greenhouse"

    # 2. Lever domain
    url, ats = crawler.resolve_career_url("Figma", "jobs.lever.co/figma")
    assert "jobs.lever.co" in url
    assert ats == "lever"

    # 3. Custom domain
    url, ats = crawler.resolve_career_url("Acme Corp", "acme.ai")
    assert "careers.acme.ai" in url
    assert ats == "custom"


def test_tech_roles_pattern():
    assert TECH_ROLES_PATTERN.search("Senior Software Engineer") is not None
    assert TECH_ROLES_PATTERN.search("Staff AI & Machine Learning Scientist") is not None
    assert TECH_ROLES_PATTERN.search("Full Stack Developer (Python/React)") is not None
    assert TECH_ROLES_PATTERN.search("Office Janitor") is None


def test_career_crawler_ats_api_mock(test_db):
    crawler = CareerPageCrawler(workspace=11, conn=test_db)

    mock_greenhouse_response = json.dumps({
        "jobs": [
            {
                "title": "Senior AI Systems Engineer",
                "absolute_url": "https://boards.greenhouse.io/acme/jobs/101",
                "location": {"name": "Remote, US"},
            },
            {
                "title": "Staff Backend Engineer",
                "absolute_url": "https://boards.greenhouse.io/acme/jobs/102",
                "location": {"name": "San Francisco, CA"},
            }
        ]
    }).encode("utf-8")

    async def _run():
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = mock_greenhouse_response
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            jobs = await crawler._try_ats_api("Acme AI", "acme.ai", "greenhouse")
            assert len(jobs) == 2
            assert jobs[0]["title"] == "Senior AI Systems Engineer"
            assert "101" in jobs[0]["url"]

    asyncio.run(_run())


def test_career_crawler_persistence(test_db):
    crawler = CareerPageCrawler(workspace=11, headless=True, conn=test_db)

    # Mock _try_ats_api returning live jobs
    sample_jobs = [
        {
            "title": "Lead Autonomous Agent Engineer",
            "url": "https://careers.acme.ai/agent-lead",
            "company": "Acme AI",
            "location": "Remote",
            "salary": "$180k - $220k",
            "description": "Leading agentic architecture with LangGraph and Python.",
        }
    ]

    async def _run():
        with patch.object(crawler, "_try_ats_api", new_callable=AsyncMock) as mock_ats, \
             patch("playwright.async_api.async_playwright") as mock_pw:

            mock_ats.return_value = sample_jobs

            # Mock playwright so unit test doesn't launch live browser binary in CI
            mock_p_instance = AsyncMock()
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()

            mock_page.eval_on_selector_all.return_value = []
            mock_page.evaluate.return_value = None
            mock_page.goto.return_value = None
            mock_page.screenshot.return_value = None
            mock_page.url = "https://careers.acme.ai"

            mock_context.new_page.return_value = mock_page
            mock_browser.new_context.return_value = mock_context
            mock_p_instance.chromium.launch.return_value = mock_browser

            mock_pw.return_value.__aenter__.return_value = mock_p_instance

            res = await crawler.crawl_live_careers("Acme AI", "acme.ai", max_jobs=5)

            assert res["total_extracted"] >= 1
            assert res["company_name"] == "Acme AI"

            # Verify SQLite jobs table has the newly discovered job
            row = test_db.execute("SELECT title, site FROM jobs WHERE company = 'Acme AI'").fetchone()
            assert row is not None
            assert row["title"] == "Lead Autonomous Agent Engineer"

            # Verify career_watchlist has the entry
            w_row = test_db.execute("SELECT company_name, open_roles_count FROM career_watchlist WHERE company_name = 'Acme AI'").fetchone()
            assert w_row is not None
            assert w_row["open_roles_count"] >= 1

    asyncio.run(_run())


def test_career_crawler_deep_navigation(test_db):
    """Test crawler detects and navigates to deep career portal links from homepage."""
    crawler = CareerPageCrawler(workspace=10, headless=True, conn=test_db, dwell_time=0.0)

    async def _run():
        with patch.object(crawler, "_try_ats_api", new_callable=AsyncMock) as mock_ats, \
             patch("playwright.async_api.async_playwright") as mock_pw:

            mock_ats.return_value = []

            mock_p_instance = AsyncMock()
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()

            # Simulate homepage discovering a careers URL
            mock_page.evaluate.side_effect = [
                "https://acme.ai/careers",  # deep career link discovered
                None,                       # scroll script
                None,                       # highlight script
            ]
            mock_page.url = "https://acme.ai"
            mock_page.goto.return_value = None
            mock_page.screenshot.return_value = None
            mock_page.eval_on_selector_all.return_value = [
                {"text": "Senior AI Infrastructure Engineer", "href": "/careers/ai-infra"}
            ]

            mock_context.new_page.return_value = mock_page
            mock_browser.new_context.return_value = mock_context
            mock_p_instance.chromium.launch.return_value = mock_browser
            mock_pw.return_value.__aenter__.return_value = mock_p_instance

            res = await crawler.crawl_live_careers("Acme Corp", "acme.ai", max_jobs=5)

            assert res["total_extracted"] == 1
            assert res["jobs"][0]["title"] == "Senior AI Infrastructure Engineer"
            # Verify page navigated to discovered deep careers link
            assert any("https://acme.ai/careers" in str(call) for call in mock_page.goto.call_args_list)

    asyncio.run(_run())


def test_find_best_matching_job():
    from applypilot.discovery.career_page_crawler import find_best_matching_job

    jobs = [
        {"title": "Account Executive", "url": "https://example.com/ae"},
        {"title": "Founding Full Stack Engineer", "url": "https://example.com/founding-eng"},
        {"title": "Customer Support Representative", "url": "https://example.com/cs"},
    ]
    title, url = find_best_matching_job(jobs)
    assert title == "Founding Full Stack Engineer"
    assert url == "https://example.com/founding-eng"

