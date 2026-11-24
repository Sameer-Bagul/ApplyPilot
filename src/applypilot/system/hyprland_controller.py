"""Hyprland Desktop & Wayland Controller for ApplyPilot.

Manages dedicated workspace routing, display geometry detection, non-stealing
focus rules, and desktop notifications for headed browser automation on Arch Linux.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from typing import Any

logger = logging.getLogger("applypilot.hyprland")

DEFAULT_WORKSPACE = 11
DEFAULT_CLASS = "ApplyPilotCrawler"


class HyprlandController:
    """Controls Hyprland compositor workspaces and window rules for browser workers."""

    def __init__(self, workspace: int = DEFAULT_WORKSPACE, window_class: str = DEFAULT_CLASS) -> None:
        self.workspace = workspace
        self.window_class = window_class
        self._hyprctl = shutil.which("hyprctl")
        self._notify_send = shutil.which("notify-send")
        self.is_hyprland = bool(
            self._hyprctl
            and (
                os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
                or os.environ.get("XDG_CURRENT_DESKTOP") == "Hyprland"
            )
        )

    def get_monitor_geometry(self) -> tuple[int, int]:
        """Detect primary monitor resolution (width, height) or fallback to 2560x1440 / 1920x1080."""
        if not self.is_hyprland or not self._hyprctl:
            return 2560, 1440

        try:
            res = subprocess.run(
                [self._hyprctl, "monitors", "-j"],
                capture_output=True,
                text=True,
                check=True,
                timeout=3,
            )
            monitors: list[dict[str, Any]] = json.loads(res.stdout)
            if monitors:
                # Prefer focused monitor or highest resolution
                focused = next((m for m in monitors if m.get("focused")), None)
                target = focused or max(monitors, key=lambda m: (m.get("width", 0) * m.get("height", 0)))
                w = int(target.get("width", 2560))
                h = int(target.get("height", 1440))
                return w, h
        except Exception as e:
            logger.debug("Failed querying Hyprland monitors: %s", e)

        return 2560, 1440

    def ensure_workspace_rules(self) -> bool:
        """Dynamically register Hyprland window rules to route browser to dedicated workspace."""
        if not self.is_hyprland or not self._hyprctl:
            return False

        try:
            # 1. Route class to dedicated workspace
            subprocess.run(
                [self._hyprctl, "keyword", "windowrulev2", f"workspace {self.workspace},class:^({self.window_class})$"],
                capture_output=True,
                timeout=3,
                check=False,
            )
            # 2. Maximize window inside workspace
            subprocess.run(
                [self._hyprctl, "keyword", "windowrulev2", f"maximize,class:^({self.window_class})$"],
                capture_output=True,
                timeout=3,
                check=False,
            )
            # 3. Do not steal focus from active coding window
            subprocess.run(
                [self._hyprctl, "keyword", "windowrulev2", f"noinitialfocus,class:^({self.window_class})$"],
                capture_output=True,
                timeout=3,
                check=False,
            )
            logger.debug("Registered Hyprland window rules for %s on workspace %d", self.window_class, self.workspace)
            return True
        except Exception as e:
            logger.debug("Error setting Hyprland rules: %s", e)
            return False

    def focus_workspace(self, workspace: int | None = None) -> bool:
        """Switch active Hyprland view to workspace on monitor HDMI-A-1."""
        if not self.is_hyprland or not self._hyprctl:
            return False
        ws = workspace or self.workspace
        try:
            # 1. Focus HDMI-A-1 monitor first
            subprocess.run(
                [self._hyprctl, "dispatch", "hl.dsp.focus_monitor({ monitor = 'HDMI-A-1' })"],
                capture_output=True,
                timeout=3,
                check=False,
            )
            # 2. Focus requested workspace using Lua syntax
            res = subprocess.run(
                [self._hyprctl, "dispatch", f"hl.dsp.focus({{ workspace = {ws} }})"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            if "ok" in res.stdout:
                return True
            # Fallback for standard Hyprland C++
            subprocess.run([self._hyprctl, "dispatch", "workspace", str(ws)], capture_output=True, timeout=3, check=False)
            return True
        except Exception as e:
            logger.debug("Failed switching to Hyprland workspace %d: %s", ws, e)
            return False

    def notify(self, title: str, message: str, urgency: str = "normal") -> None:
        """Emit desktop notification via notify-send if available."""
        if not self._notify_send or not os.environ.get("WAYLAND_DISPLAY"):
            return
        try:
            subprocess.run(
                [self._notify_send, "-a", "ApplyPilot", "-u", urgency, "-i", "applications-internet", title, message],
                capture_output=True,
                timeout=3,
                check=False,
            )
        except Exception:
            pass

    def get_playwright_launch_config(
        self,
        headless: bool = False,
    ) -> dict[str, Any]:
        """Construct Chromium launch kwargs and args optimized for Wayland/Hyprland."""
        w, h = self.get_monitor_geometry()

        args = [
            f"--class={self.window_class}",
            f"--app-id={self.window_class}",
            f"--window-size={w},{h}",
            "--start-maximized",
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-infobars",
        ]

        # Use native Wayland backend if available
        if os.environ.get("WAYLAND_DISPLAY"):
            args.extend(["--ozone-platform-hint=auto"])

        self.ensure_workspace_rules()

        return {
            "headless": headless,
            "args": args,
            "viewport": {"width": w, "height": h},
        }

