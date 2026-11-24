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


@pytest.mark.anyio
async def test_detect_challenge_hcaptcha_nested_frame():
    """Verify detection of hCaptcha odd-one-out icon challenge inside nested subframe."""
    mock_frame = MagicMock()
    mock_frame.url = "https://newassets.hcaptcha.com/captcha/v1/12345/static/hcaptcha.html#frame=challenge"
    mock_frame.evaluate = AsyncMock(return_value="Please click on the TWO icons that are different from the others\nSkip\nEN")

    mock_page = MagicMock()
    mock_page.title = AsyncMock(return_value="Job Application")
    mock_page.frames = [mock_frame]
    mock_page.query_selector_all = AsyncMock(return_value=[])

    challenge = await detect_challenge(mock_page)
    assert challenge is not None
    assert challenge["type"] == "hcaptcha"
    assert "hCaptcha" in challenge["name"]
    assert "Active hCaptcha prompt" in challenge["detail"]


@pytest.mark.anyio
async def test_detect_challenge_hcaptcha_visible_modal_iframe():
    """Verify detection of full-screen hCaptcha modal iframe on Lever."""
    mock_iframe = MagicMock()
    mock_iframe.is_visible = AsyncMock(return_value=True)
    mock_iframe.bounding_box = AsyncMock(return_value={"width": 1280, "height": 720, "x": 0, "y": 0})
    mock_iframe.get_attribute = AsyncMock(side_effect=lambda attr: {
        "title": "Widget containing checkbox for hCaptcha security challenge",
        "src": "https://newassets.hcaptcha.com/captcha/v1/static/hcaptcha-enclave.html#frame=enclave",
    }.get(attr))

    mock_page = MagicMock()
    mock_page.title = AsyncMock(return_value="BTSE - Senior QA Engineer")
    mock_page.frames = []
    mock_page.query_selector_all = AsyncMock(return_value=[mock_iframe])

    challenge = await detect_challenge(mock_page)
    assert challenge is not None
    assert challenge["type"] == "hcaptcha"
    assert "Visible hCaptcha modal" in challenge["detail"]


@pytest.mark.anyio
async def test_detect_challenge_arkose_funcaptcha():
    """Verify detection of Arkose Labs / FunCaptcha modal."""
    mock_frame = MagicMock()
    mock_frame.url = "https://client-api.arkoselabs.com/fc/api/?token=xyz"
    mock_frame.evaluate = AsyncMock(return_value="Please solve this puzzle\nAudio\nVerify")

    mock_page = MagicMock()
    mock_page.title = AsyncMock(return_value="Careers")
    mock_page.frames = [mock_frame]
    mock_page.query_selector_all = AsyncMock(return_value=[])

    challenge = await detect_challenge(mock_page)
    assert challenge is not None
    assert challenge["type"] == "funcaptcha"
    assert "Arkose" in challenge["name"]

