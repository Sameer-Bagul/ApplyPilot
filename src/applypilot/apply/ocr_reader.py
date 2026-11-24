"""OCR recognition layer for visual page status and ATS banner verification.

Extracts text from viewport screenshots using system Tesseract OCR to detect
visual-only banners, error illustrations, and closed job alerts that bypass DOM text checks.
"""

import asyncio
import logging
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Common phrases indicating a dead, expired, or non-existent job posting
CLOSED_OR_MISSING_PATTERNS = [
    r"\bjob\s+(?:is\s+)?not\s+found\b",
    r"\bpage\s+not\s+found\b",
    r"\b404\s+(?:not\s+found)?\b",
    r"\bposition\s+(?:is\s+)?not\s+found\b",
    r"\bjob\s+(?:is\s+)?no\s+longer\s+available\b",
    r"\bposition\s+has\s+been\s+filled\b",
    r"\b(?:job|posting)\s+has\s+expired\b",
    r"\bno\s+longer\s+accepting\s+applications\b",
    r"\bposition\s+is\s+no\s+longer\s+open\b",
    r"\bthis\s+position\s+is\s+closed\b",
    r"\bthis\s+job\s+is\s+closed\b",
    r"\bthis\s+requisition\s+is\s+closed\b",
    r"\bwe\s+couldn'?t\s+find\s+anything\b",
    r"\bmight\s+have\s+closed,?\s+or\s+it\s+has\s+been\s+removed\b",
    r"\bno\s+longer\s+open\s+for\s+applications\b",
    r"\bcareer\s+opportunity\s+is\s+no\s+longer\s+available\b",
    r"\bthis\s+posting\s+is\s+inactive\b",
    r"\bjob\s+has\s+been\s+unposted\b",
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in CLOSED_OR_MISSING_PATTERNS]


def get_tesseract_binary() -> str | None:
    """Find the path to the Tesseract binary."""
    return shutil.which("tesseract") or ("/usr/bin/tesseract" if Path("/usr/bin/tesseract").exists() else None)


async def extract_text_from_image(image_path: str | Path, timeout_sec: float = 8.0) -> str:
    """Extract text from an image file using system Tesseract.

    Args:
        image_path: Path to PNG or JPEG image.
        timeout_sec: Maximum time allowed for OCR execution.

    Returns:
        Extracted text string, or empty string on failure.
    """
    tesseract_bin = get_tesseract_binary()
    if not tesseract_bin:
        logger.warning("Tesseract OCR binary not found on system PATH.")
        return ""

    img_path = Path(image_path)
    if not img_path.exists():
        logger.warning("Image file for OCR does not exist: %s", image_path)
        return ""

    try:
        proc = await asyncio.create_subprocess_exec(
            tesseract_bin,
            str(img_path),
            "stdout",
            "--oem", "1",
            "-l", "eng",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            logger.warning("Tesseract OCR timed out after %0.1fs on %s", timeout_sec, image_path)
            return ""

        if proc.returncode == 0:
            return stdout.decode("utf-8", errors="replace").strip()
        else:
            err_msg = stderr.decode("utf-8", errors="replace").strip()
            logger.debug("Tesseract returned code %d: %s", proc.returncode, err_msg)
            return ""
    except Exception as e:
        logger.warning("Tesseract OCR execution error: %s", e)
        return ""


async def ocr_page_viewport(page: Any, timeout_sec: float = 4.0) -> str:
    """Capture a fast viewport screenshot of the current page and run OCR.

    Args:
        page: Playwright Page instance.
        timeout_sec: Timeout for screenshot + OCR.

    Returns:
        Recognized text from the page viewport.
    """
    if not hasattr(page, "screenshot") or not callable(page.screenshot):
        return ""

    # Don't capture if page is closed
    if hasattr(page, "is_closed") and callable(page.is_closed):
        try:
            if page.is_closed():
                return ""
        except Exception:
            return ""

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
        tmp_path = Path(tmp_file.name)

    try:
        screenshot_coro = page.screenshot(path=str(tmp_path), full_page=False, timeout=3000)
        if asyncio.iscoroutine(screenshot_coro):
            await screenshot_coro

        return await extract_text_from_image(tmp_path, timeout_sec=timeout_sec)
    except Exception as e:
        logger.debug("ocr_page_viewport failed: %s", e)
        return ""
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


def detect_closed_or_missing_job_from_ocr(ocr_text: str) -> tuple[bool, str]:
    """Inspect OCR text for visual signals of expired, missing, or closed jobs.

    Args:
        ocr_text: Raw string extracted from viewport.

    Returns:
        (is_closed, reason) tuple.
    """
    if not ocr_text:
        return False, ""

    clean_text = " ".join(ocr_text.split())
    for pattern in _COMPILED_PATTERNS:
        match = pattern.search(clean_text)
        if match:
            matched_phrase = match.group(0)
            return True, f"OCR visual detection: '{matched_phrase}'"

    return False, ""

