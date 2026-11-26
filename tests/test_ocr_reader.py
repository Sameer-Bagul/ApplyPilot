"""Unit tests for OCR reader and visual closed/missing job detection."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from applypilot.apply.ocr_reader import (
    CLOSED_OR_MISSING_PATTERNS,
    SUCCESS_SUBMISSION_PATTERNS,
    detect_closed_or_missing_job_from_ocr,
    detect_submission_success_from_ocr,
    extract_text_from_image,
    get_tesseract_binary,
    ocr_page_viewport,
    verify_submission_image_with_ai,
)


def test_get_tesseract_binary():
    binary = get_tesseract_binary()
    assert binary is not None
    assert "tesseract" in binary


def test_detect_closed_or_missing_job_from_ocr():
    assert detect_closed_or_missing_job_from_ocr("")[0] is False
    assert detect_closed_or_missing_job_from_ocr("Welcome to our careers page. Apply below.")[0] is False

    # Test key error phrases
    closed_cases = [
        "Oops! Job not found. Please browse other open positions.",
        "Error 404 - Page not found",
        "We are sorry, this position has been filled.",
        "Notice: Job has expired.",
        "The company is no longer accepting applications for this role.",
        "Sorry, we couldn't find anything here.",
        "This position is closed.",
    ]
    for case in closed_cases:
        is_closed, reason = detect_closed_or_missing_job_from_ocr(case)
        assert is_closed is True, f"Failed to detect: {case}"
        assert len(reason) > 0


@pytest.mark.anyio
async def test_extract_text_from_image_missing_file():
    text = await extract_text_from_image("/tmp/non_existent_image_12345.png")
    assert text == ""


@pytest.mark.anyio
async def test_ocr_page_viewport_mock():
    mock_page = MagicMock()
    mock_page.is_closed.return_value = False
    mock_page.screenshot = AsyncMock()

    with patch("applypilot.apply.ocr_reader.extract_text_from_image", new=AsyncMock(return_value="Position has been filled")):
        text = await ocr_page_viewport(mock_page)
        assert text == "Position has been filled"
        mock_page.screenshot.assert_called_once()


def test_detect_submission_success_from_ocr():
    assert detect_submission_success_from_ocr("")[0] is False
    assert detect_submission_success_from_ocr("Please enter your name and email address.")[0] is False

    success_cases = [
        "Thank you for applying to Stripe! We have received your application.",
        "Your application was submitted successfully.",
        "We've received your submission. Our team will review your application shortly.",
        "Thanks for applying! You have successfully applied.",
        "Application received. We look forward to reviewing your application.",
    ]
    for case in success_cases:
        is_success, phrase = detect_submission_success_from_ocr(case)
        assert is_success is True, f"Failed to detect success for: {case}"
        assert len(phrase) > 0


@pytest.mark.anyio
async def test_verify_submission_image_with_ai_mock(tmp_path):
    img = tmp_path / "test_screen.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\nfakeimagecontent")

    # With no key configured
    with patch.dict("os.environ", {}, clear=True):
        ok, reason = await verify_submission_image_with_ai(img)
        assert ok is False

    # Mocked Gemini Vision API
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{
            "content": {
                "parts": [{"text": '{"confirmed": true, "reason": "Thank you for applying banner visible"}'}]
            }
        }]
    }

    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_gemini_key"}):
        with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp)):
            ok, reason = await verify_submission_image_with_ai(img)
            assert ok is True
            assert "Thank you for applying" in reason


