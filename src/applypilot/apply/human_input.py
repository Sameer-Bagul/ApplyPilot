"""Dynamic Human-Like Input and Keystroke Interaction Engine.

Provides organic, realistic human typing cadence, randomized keystroke intervals,
natural cognitive pauses, smooth scrolling, and human-like click behaviors for Playwright.
Defeats modern behavioral anti-bot heuristics (Cloudflare, PerimeterX, Datadome)
and provides a natural, visually pleasing recording in headed desktop mode.
"""

from __future__ import annotations

import asyncio
import logging
import random
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


async def human_pause(min_sec: float = 0.15, max_sec: float = 0.35) -> None:
    """Pause execution for a natural human reaction interval."""
    await asyncio.sleep(random.uniform(min_sec, max_sec))


async def human_type(
    locator: Any,
    text: str,
    page: Any = None,
    clear_first: bool = True,
    fast_mode: bool = False,
) -> None:
    """Type text into a locator using dynamic, human-like cadence.

    Features:
    - Smooth scroll into view
    - Realistic mouse click focus
    - Dynamic inter-keystroke intervals with human jitter
    - Punctuation and whitespace cognitive pauses
    - Natural burst typing for long passages (summaries, essays)
    - Realistic post-fill dwell time
    """
    if not text:
        return

    val_str = str(text)

    try:
        if hasattr(locator, "scroll_into_view_if_needed") and callable(locator.scroll_into_view_if_needed):
            await locator.scroll_into_view_if_needed(timeout=2000)
    except Exception:
        pass

    try:
        # Focus element with natural click delay
        await locator.click(delay=random.randint(35, 85), timeout=2500)
        await asyncio.sleep(random.uniform(0.06, 0.14))
    except Exception:
        pass

    if clear_first:
        try:
            # Select all and clear naturally
            await locator.press("ControlOrMeta+A")
            await asyncio.sleep(0.04)
            await locator.press("Backspace")
            await asyncio.sleep(0.05)
        except Exception:
            pass

    # Fast mode (if specified) or very short strings
    if fast_mode:
        await locator.press_sequentially(val_str, delay=random.randint(12, 28))
        await asyncio.sleep(random.uniform(0.1, 0.2))
        return

    # For long passages (e.g. cover letters, summaries > 80 chars),
    # type in human rhythmic bursts of 3-8 characters
    if len(val_str) > 80:
        i = 0
        while i < len(val_str):
            chunk_size = random.randint(3, 8)
            chunk = val_str[i : i + chunk_size]
            char_delay = random.randint(10, 24)
            await locator.press_sequentially(chunk, delay=char_delay)
            i += chunk_size

            # Inter-burst dwell
            if i < len(val_str):
                last_char = chunk[-1] if chunk else ""
                if last_char in ".,;!?\n":
                    await asyncio.sleep(random.uniform(0.12, 0.22))
                elif last_char == " ":
                    await asyncio.sleep(random.uniform(0.04, 0.09))
                else:
                    await asyncio.sleep(random.uniform(0.02, 0.06))
    else:
        # Character-by-character typing with realistic cadence and jitter
        for idx, char in enumerate(val_str):
            await locator.press_sequentially(char, delay=0)

            # Base keystroke delay (approx 45-85 WPM)
            delay = random.uniform(0.022, 0.058)

            # Natural punctuation pauses
            if char in " ,.@-_/":
                delay += random.uniform(0.05, 0.11)
            elif random.random() < 0.035:
                # 3.5% chance of cognitive micro-hesitation
                delay += random.uniform(0.09, 0.18)

            await asyncio.sleep(delay)

    # Post-fill field dwell time (visual verification before moving to next field)
    await asyncio.sleep(random.uniform(0.12, 0.28))


async def human_click(locator: Any, page: Any = None, wait_after_sec: float = 0.3) -> None:
    """Click an element with human cursor focus and deliberate button press."""
    try:
        if hasattr(locator, "scroll_into_view_if_needed") and callable(locator.scroll_into_view_if_needed):
            await locator.scroll_into_view_if_needed(timeout=2000)
    except Exception:
        pass

    await asyncio.sleep(random.uniform(0.08, 0.18))
    await locator.click(delay=random.randint(55, 125))
    await asyncio.sleep(random.uniform(wait_after_sec * 0.7, wait_after_sec * 1.3))


async def human_select(locator: Any, label: str, page: Any = None) -> None:
    """Select a dropdown option with human visual hesitation."""
    try:
        if hasattr(locator, "scroll_into_view_if_needed") and callable(locator.scroll_into_view_if_needed):
            await locator.scroll_into_view_if_needed(timeout=2000)
    except Exception:
        pass

    await asyncio.sleep(random.uniform(0.1, 0.25))
    await locator.select_option(label=str(label))
    await asyncio.sleep(random.uniform(0.15, 0.35))


async def human_check(locator: Any, page: Any = None) -> None:
    """Check a radio or checkbox element with realistic mouse movement."""
    try:
        if hasattr(locator, "scroll_into_view_if_needed") and callable(locator.scroll_into_view_if_needed):
            await locator.scroll_into_view_if_needed(timeout=2000)
    except Exception:
        pass

    await asyncio.sleep(random.uniform(0.08, 0.18))
    await locator.check()
    await asyncio.sleep(random.uniform(0.12, 0.25))


async def human_upload(locator: Any, file_path: str, page: Any = None) -> None:
    """Attach a file with human hesitation before dialog interaction."""
    if not file_path or not Path(file_path).exists():
        return

    try:
        if hasattr(locator, "scroll_into_view_if_needed") and callable(locator.scroll_into_view_if_needed):
            await locator.scroll_into_view_if_needed(timeout=2000)
    except Exception:
        pass

    await asyncio.sleep(random.uniform(0.2, 0.45))
    await locator.set_input_files(str(file_path))
    await asyncio.sleep(random.uniform(0.35, 0.65))
