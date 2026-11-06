"""Audible alert and sound system for ApplyPilot Human-in-the-Loop (HITL).

Provides cross-platform sound playback using:
1. Linux system audio (paplay, pw-play, canberra-gtk-play, aplay)
2. In-browser Web Audio API synthesis (AudioContext via Playwright page.evaluate)
3. Terminal bell characters (\\a)
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
import time
from typing import Literal

logger = logging.getLogger(__name__)

# Standard Linux freedesktop sound paths
_SOUND_FILES: dict[str, list[str]] = {
    "alert": [
        "/usr/share/sounds/freedesktop/stereo/dialog-warning.oga",
        "/usr/share/sounds/freedesktop/stereo/bell.oga",
        "/usr/share/sounds/freedesktop/stereo/message-new-instant.oga",
    ],
    "success": [
        "/usr/share/sounds/freedesktop/stereo/complete.oga",
        "/usr/share/sounds/freedesktop/stereo/bell.oga",
    ],
    "chime": [
        "/usr/share/sounds/freedesktop/stereo/message.oga",
        "/usr/share/sounds/freedesktop/stereo/bell.oga",
        "/usr/share/sounds/freedesktop/stereo/complete.oga",
    ],
}


def _find_audio_player() -> tuple[str | None, list[str]]:
    """Locate available audio player CLI on the system."""
    for cmd in ["paplay", "pw-play", "aplay"]:
        if shutil.which(cmd):
            return cmd, [cmd]
    if shutil.which("canberra-gtk-play"):
        return "canberra-gtk-play", ["canberra-gtk-play"]
    return None, []


def play_system_sound(kind: Literal["alert", "success", "chime"] = "alert") -> bool:
    """Play an audible system sound in the background non-blockingly."""
    try:
        # 1. Ring terminal bell
        print("\a", end="", flush=True)
    except Exception:
        pass

    player_name, base_cmd = _find_audio_player()
    if not player_name:
        return False

    candidates = _SOUND_FILES.get(kind, _SOUND_FILES["alert"])
    target_file = None
    for f in candidates:
        if os.path.exists(f):
            target_file = f
            break

    if not target_file and player_name != "canberra-gtk-play":
        return False

    def _worker():
        try:
            if player_name == "canberra-gtk-play":
                event_name = "dialog-warning" if kind == "alert" else "complete"
                subprocess.run(
                    ["canberra-gtk-play", "-i", event_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                )
            elif target_file:
                subprocess.run(
                    base_cmd + [target_file],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                )
        except Exception as e:
            logger.debug("Failed playing system sound: %s", e)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return True


async def play_browser_chime(page: Any, tone: Literal["alert", "success", "chime"] = "alert") -> None:
    """Synthesize and play an audible tone directly inside the headed browser window."""
    try:
        script = """
        (kind) => {
            try {
                const AudioCtx = window.AudioContext || window.webkitAudioContext;
                if (!AudioCtx) return;
                const ctx = new AudioCtx();
                if (ctx.state === 'suspended') {
                    ctx.resume();
                }

                const now = ctx.currentTime;
                const gain = ctx.createGain();
                gain.connect(ctx.destination);

                if (kind === 'alert') {
                    // Two-tone warning beep: 660Hz -> 880Hz -> 660Hz
                    gain.gain.setValueAtTime(0.3, now);
                    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.7);

                    const osc = ctx.createOscillator();
                    osc.type = 'triangle';
                    osc.frequency.setValueAtTime(660, now);
                    osc.frequency.setValueAtTime(880, now + 0.18);
                    osc.frequency.setValueAtTime(660, now + 0.36);
                    osc.connect(gain);
                    osc.start(now);
                    osc.stop(now + 0.7);
                } else if (kind === 'success') {
                    // Ascending major chord chime (C5 -> E5 -> G5)
                    gain.gain.setValueAtTime(0.25, now);
                    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.6);

                    const osc1 = ctx.createOscillator();
                    osc1.type = 'sine';
                    osc1.frequency.setValueAtTime(523.25, now); // C5
                    osc1.frequency.setValueAtTime(659.25, now + 0.15); // E5
                    osc1.frequency.setValueAtTime(783.99, now + 0.3); // G5
                    osc1.connect(gain);
                    osc1.start(now);
                    osc1.stop(now + 0.6);
                } else {
                    // Gentle chime
                    gain.gain.setValueAtTime(0.2, now);
                    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.5);
                    const osc = ctx.createOscillator();
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(587.33, now); // D5
                    osc.frequency.setValueAtTime(880, now + 0.15); // A5
                    osc.connect(gain);
                    osc.start(now);
                    osc.stop(now + 0.5);
                }
            } catch (err) {
                // AudioContext may be restricted by autoplay policy until user gesture
            }
        }
        """
        await page.evaluate(script, tone)
    except Exception as e:
        logger.debug("Browser chime evaluate failed: %s", e)


def notify_hitl_needed(page: Any = None, reason: str = "CAPTCHA or security challenge") -> None:
    """Trigger full multi-tier audio notification (system sound + terminal bell + browser chime)."""
    play_system_sound("alert")
    if page:
        try:
            import asyncio
            # If in async loop, schedule browser chime
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(play_browser_chime(page, "alert"))
        except Exception:
            pass


def notify_hitl_resolved(page: Any = None) -> None:
    """Trigger success audio notification."""
    play_system_sound("success")
    if page:
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(play_browser_chime(page, "success"))
        except Exception:
            pass
