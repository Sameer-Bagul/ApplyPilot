import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from applypilot.hitl.audio import (
    play_system_sound,
    play_browser_chime,
    notify_hitl_needed,
    notify_hitl_resolved,
)
from applypilot.apply.captcha_detector import (
    detect_challenge,
    is_challenge_solved,
    inject_hitl_banner,
    remove_hitl_banner,
    wait_for_human_challenge_resolution,
)


def test_play_system_sound():
    # Should run non-blockingly without throwing
    res = play_system_sound("alert")
    assert isinstance(res, bool)
    res_success = play_system_sound("success")
    assert isinstance(res_success, bool)


@pytest.mark.anyio
async def test_play_browser_chime():
    mock_page = MagicMock()
    mock_page.evaluate = AsyncMock(return_value=None)
    await play_browser_chime(mock_page, "alert")
    assert mock_page.evaluate.called


@pytest.mark.anyio
async def test_detect_challenge_turnstile():
    mock_page = MagicMock()
    mock_page.title = AsyncMock(return_value="Acme Careers Application")
    mock_page.evaluate = AsyncMock(return_value={
        "type": "turnstile",
        "name": "Cloudflare Turnstile",
        "selector": ".cf-turnstile",
    })

    challenge = await detect_challenge(mock_page)
    assert challenge is not None
    assert challenge["type"] == "turnstile"
    assert challenge["name"] == "Cloudflare Turnstile"


@pytest.mark.anyio
async def test_detect_challenge_bot_gate():
    mock_page = MagicMock()
    mock_page.title = AsyncMock(return_value="Just a moment... | Cloudflare")
    challenge = await detect_challenge(mock_page)
    assert challenge is not None
    assert challenge["type"] == "bot_gate"


@pytest.mark.anyio
async def test_is_challenge_solved():
    mock_page = MagicMock()
    mock_page.evaluate = AsyncMock(return_value=True)
    solved = await is_challenge_solved(mock_page, {"type": "turnstile"})
    assert solved is True


@pytest.mark.anyio
async def test_inject_and_remove_banner():
    mock_page = MagicMock()
    mock_page.evaluate = AsyncMock(return_value=None)
    await inject_hitl_banner(mock_page, "Test Banner")
    assert mock_page.evaluate.called
    await remove_hitl_banner(mock_page)
    assert mock_page.evaluate.call_count == 2


@pytest.mark.anyio
async def test_wait_for_human_challenge_resolution_success():
    mock_page = MagicMock()
    mock_page.url = "https://boards.greenhouse.io/acme/jobs/123"
    mock_page.wait_for_timeout = AsyncMock()
    # First check False, second check True
    with patch("applypilot.apply.captcha_detector.is_challenge_solved", AsyncMock(side_effect=[False, True])):
        with patch("applypilot.apply.captcha_detector.notify_hitl_needed") as mock_alert:
            with patch("applypilot.apply.captcha_detector.notify_hitl_resolved") as mock_res:
                resolved = await wait_for_human_challenge_resolution(
                    mock_page,
                    {"type": "turnstile", "name": "Cloudflare Turnstile"},
                    timeout_sec=5,
                    check_interval=0.05,
                )
                assert resolved is True
                assert mock_alert.called
                assert mock_res.called
