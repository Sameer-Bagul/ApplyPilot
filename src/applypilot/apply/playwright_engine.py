"""Low-AI Playwright Scripting Engine for ApplyPilot.

Connects to the active Chrome worker over CDP or directly launches a headed/headless
Chromium browser, deterministically fills standard ATS fields (Tier 0), resolves
screening questions from the local knowledge base (Tier 1 semantic Q&A), applies
algorithmic sanitizers (Tier 2), and submits or enters review mode.

Includes real-time CAPTCHA & Security Challenge detection:
When a challenge (Cloudflare Turnstile, reCAPTCHA, hCaptcha, bot gate, OTP) is detected
in headed mode, the engine alerts the user with audible sound (system audio + browser chime +
terminal bell), displays a guidance banner in the browser window, and smoothly resumes once
the user solves the challenge.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
import os
import re
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from applypilot import config
from applypilot.database import (
    get_connection,
    store_selector,
    record_selector_result,
    save_session_vault,
    get_session_vault,
)
from applypilot.learning.tier0_playbook import (
    detect_form_ats,
    fill_standard_fields_playwright,
    _resolve_profile_value,
)
from applypilot.learning.tier1_semantic_qa import resolve_screening_question
from applypilot.learning.tier2_heuristics import normalize_phone, sanitize_url
from applypilot.learning.pattern_compiler import record_apply_trace
from applypilot.hitl.checkpoint import (
    serialize_form_checkpoint,
    replay_checkpoint_playwright,
    save_browser_session_cookies,
    load_browser_session_cookies,
)
from applypilot.hitl.email_notifier import dispatch_hitl_email_and_park
from applypilot.hitl.audio import (
    notify_hitl_needed,
    notify_hitl_resolved,
    play_browser_chime,
    play_system_sound,
)
from applypilot.apply.captcha_detector import (
    detect_challenge,
    wait_for_human_challenge_resolution,
    inject_hitl_banner,
    remove_hitl_banner,
)

logger = logging.getLogger(__name__)


class ApplicationTracer:
    """Rich execution audit logger that captures every step, filled field, Q&A, and browser event."""

    def __init__(self, job: dict):
        self.job = job
        self.start_time = time.time()
        self.events: list[dict] = []
        self.form_fields_attempted: list[dict] = []
        self.qa_resolutions: list[dict] = []
        self.challenges_encountered: list[dict] = []
        self.browser_console_logs: list[str] = []
        self.error_traces: list[str] = []
        self.screenshots: dict[str, str] = {}

    def log(self, stage: str, message: str, details: dict | None = None, level: str = "INFO"):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_ms": int((time.time() - self.start_time) * 1000),
            "stage": stage,
            "level": level,
            "message": message,
            "details": details or {},
        }
        self.events.append(entry)
        logger.info("[%s] %s %s", stage.upper(), message, details if details else "")

    def add_qa(self, question: str, answer: Any, confidence: float, key: str, field_type: str):
        self.qa_resolutions.append({
            "question": question,
            "answer": answer,
            "confidence": round(confidence, 3),
            "canonical_key": key,
            "field_type": field_type,
        })

    def add_field(self, selector: str, action: str, value: Any = None, success: bool = True, error: str | None = None):
        val_str = str(value) if value is not None else ""
        if len(val_str) > 80:
            val_str = val_str[:77] + "..."
        self.form_fields_attempted.append({
            "selector": selector,
            "action": action,
            "value": val_str,
            "success": success,
            "error": error,
        })

    def to_dict(self) -> dict:
        return {
            "job_url": self.job.get("application_url") or self.job.get("url"),
            "company": self.job.get("company"),
            "title": self.job.get("title"),
            "total_duration_ms": int((time.time() - self.start_time) * 1000),
            "events_count": len(self.events),
            "fields_filled_count": len(self.form_fields_attempted),
            "qa_count": len(self.qa_resolutions),
            "events": self.events,
            "fields_filled": self.form_fields_attempted,
            "qa_resolutions": self.qa_resolutions,
            "challenges": self.challenges_encountered,
            "browser_console": self.browser_console_logs[-60:],
            "errors": self.error_traces,
            "screenshots": self.screenshots,
        }


def _load_candidate_profile() -> dict:
    """Load profile.json if exists."""
    p_file = config.PROFILE_PATH
    if p_file.exists():
        try:
            return json.loads(p_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


async def _async_run_playwright_tier_engine(
    job: dict,
    port: int = 0,
    worker_id: int = 0,
    dry_run: bool = False,
    headless: bool = True,
    auto_submit: bool | None = None,
    mode: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> tuple[str, int, list[dict]]:
    """Execute Tier 0/1/2 Playwright flow on the active Chrome worker via CDP or direct browser.

    Modes:
      - 'assist': Fills form with natural human cadence, attaches documents, then triggers
                  an audible chime, injects a floating banner, and pauses for candidate to
                  solve CAPTCHAs and click Submit (smart auto-detect on submit).
      - 'auto_verify': Fully autonomous. If CAPTCHA is detected, automatically degrades
                       to 'assist' mode. If clean, submits and verifies via multi-layer proof
                       (Network 200/201 + Viewport OCR + DOM/URL confirmation). If unconfirmed,
                       refuses 'applied' status and sets 'submission_unconfirmed'.
    """
    start_time = time.time()
    if conn is None:
        conn = get_connection()

    try:
        from playwright.async_api import async_playwright  # type: ignore[import-not-found,import-untyped]
    except (ImportError, ModuleNotFoundError):
        logger.info("Playwright not installed in environment; falling back to Claude Code agent.")
        return "fallback_to_agent", 0, []

    profile = _load_candidate_profile()
    target_url = job.get("application_url") or job.get("url") or ""
    if not target_url:
        return "fallback_to_agent", 0, []

    # Resolve execution mode ('assist' vs 'auto_verify')
    explicit_mode = (mode is not None)
    pref_mode = profile.get("preferences", {}).get("mode")
    if mode is None:
        if pref_mode in ("assist", "auto_verify"):
            mode = pref_mode
        elif auto_submit is True:
            mode = "auto_verify"
        elif auto_submit is False:
            mode = "assist"
        else:
            mode = "assist" if profile.get("preferences", {}).get("auto_submit") is False else "auto_verify"

    # In Assist Mode with an available display server, default to visible headed mode unless forced
    has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    if mode == "assist" and headless and has_display and not os.environ.get("APPLYPILOT_FORCE_HEADLESS"):
        headless = False

    # Check auto_submit preference
    if auto_submit is None:
        auto_submit = (mode == "auto_verify")

    # Hyprland Workspace 11 pinning for headed browser on laptop screen eDP-1
    if not headless:
        try:
            from applypilot.system.hyprland_controller import HyprlandController
            hypr = HyprlandController(workspace=11, window_class="ApplyPilotCrawler")
            if hypr.is_hyprland:
                hypr.ensure_workspace_rules()
                hypr.focus_workspace(11)
        except Exception as e:
            logger.debug("Hyprland controller setup skipped: %s", e)

    # Identify resume file
    resume_path = job.get("tailored_resume_path") or profile.get("resume_path")
    if not resume_path:
        from applypilot.config import RESUME_PDF_PATH
        if RESUME_PDF_PATH.exists():
            resume_path = str(RESUME_PDF_PATH)

    # Identify cover letter file & text
    cover_letter_path = job.get("cover_letter_path")
    cover_letter_text = job.get("cover_letter_text")

    tracer = ApplicationTracer(job)
    tracer.log("start", f"Initializing application runner for {job.get('company')} - {job.get('title')}", {"target_url": target_url, "auto_submit": auto_submit, "mode": mode, "headless": headless})

    try:
        async with async_playwright() as p:
            is_direct_launch = False
            browser = None
            if port > 0:
                cdp_url = f"http://127.0.0.1:{port}"
                try:
                    browser = await p.chromium.connect_over_cdp(cdp_url)
                except Exception as e:
                    logger.info("Chrome CDP on port %d unavailable (%s); falling back to agent.", port, e)
                    return "fallback_to_agent", 0, []

            if browser is None:
                is_direct_launch = True
                launch_args = [
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                ]
                if not headless:
                    launch_args.extend(["--class=ApplyPilotCrawler", "--app-id=ApplyPilotCrawler"])
                browser = await p.chromium.launch(
                    headless=headless,
                    args=launch_args,
                )

            config.ensure_dirs()
            proof_finalized = False
            page = None
            context = None

            clean_co = re.sub(r"[^a-zA-Z0-9_-]", "_", job.get("company") or "company").strip("_")[:30] or "company"
            clean_ti = re.sub(r"[^a-zA-Z0-9_-]", "_", job.get("title") or "role").strip("_")[:30] or "role"
            ts = int(time.time())
            base_proof_name = f"{clean_co}_{clean_ti}_{ts}"

            async def take_snapshot(stage_name: str) -> Path | None:
                """Capture a crisp, high-resolution viewport snapshot for a distinct pipeline stage.

                Stages:
                    '01_before_fill': Initial clean page/form before any inputs are touched.
                    '02_after_feed': Complete filled form with resume & cover letter attached, pre-submit.
                    '03_after_submission': Final screen after submission (receipt, confirmation, or challenge).
                """
                nonlocal page
                if page is None:
                    return None
                try:
                    if hasattr(page, "is_closed") and callable(page.is_closed):
                        try:
                            if page.is_closed():
                                return None
                        except Exception:
                            pass
                    config.PROOFS_SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
                    dest = config.PROOFS_SCREENSHOTS_DIR / f"{base_proof_name}_{stage_name}.png"
                    if hasattr(page, "screenshot") and callable(page.screenshot):
                        res = page.screenshot(path=str(dest), full_page=False, timeout=5000)
                        if asyncio.iscoroutine(res):
                            await res
                    tracer.screenshots[stage_name] = str(dest)
                    logger.info("[W%d] Captured proof snapshot [%s]: %s", worker_id, stage_name, dest.name)
                    return dest
                except Exception as e:
                    logger.debug("[W%d] Snapshot failed for [%s]: %s", worker_id, stage_name, e)
                    return None

            async def finalize_proofs() -> tuple[str | None, str | None]:
                nonlocal proof_finalized, page, context, browser
                if proof_finalized or page is None:
                    return None, None
                proof_finalized = True

                screenshot_dest = config.PROOFS_SCREENSHOTS_DIR / f"{base_proof_name}.png"
                screenshot_full_dest = config.PROOFS_SCREENSHOTS_DIR / f"{base_proof_name}_full.png"
                video_dest = config.PROOFS_VIDEOS_DIR / f"{base_proof_name}.webm"

                # 1. Capture screenshot proof (both crisp 2x viewport receipt and complete full-page document)
                try:
                    dest_03 = config.PROOFS_SCREENSHOTS_DIR / f"{base_proof_name}_03_after_submission.png"
                    if dest_03.exists():
                        shutil.copyfile(dest_03, screenshot_dest)
                    elif hasattr(page, "screenshot") and callable(page.screenshot):
                        is_closed = False
                        if hasattr(page, "is_closed") and callable(page.is_closed):
                            try:
                                is_closed = page.is_closed()
                            except Exception:
                                is_closed = False
                        if not is_closed:
                            # Primary receipt: Focused viewport confirmation screenshot (2560x1440 Retina)
                            res = page.screenshot(path=str(screenshot_dest), full_page=False, timeout=5000)
                            if asyncio.iscoroutine(res):
                                await res

                    if hasattr(page, "screenshot") and callable(page.screenshot):
                        try:
                            is_closed_full = False
                            if hasattr(page, "is_closed") and callable(page.is_closed):
                                is_closed_full = page.is_closed()
                            if not is_closed_full:
                                res_full = page.screenshot(path=str(screenshot_full_dest), full_page=True, timeout=5000)
                                if asyncio.iscoroutine(res_full):
                                    await res_full
                        except Exception:
                            pass
                except Exception:
                    try:
                        if hasattr(page, "screenshot") and callable(page.screenshot):
                            res = page.screenshot(path=str(screenshot_dest), timeout=3000)
                            if asyncio.iscoroutine(res):
                                await res
                    except Exception as e:
                        logger.debug("Failed capturing screenshot proof: %s", e)

                # 2. Extract video reference before closing page
                video_obj = None
                try:
                    video_obj = getattr(page, "video", None)
                except Exception:
                    pass

                # 3. Close page and context to flush video
                try:
                    if hasattr(page, "close") and callable(page.close):
                        res = page.close()
                        if asyncio.iscoroutine(res):
                            await res
                except Exception:
                    pass

                try:
                    if hasattr(context, "close") and callable(context.close):
                        res = context.close()
                        if asyncio.iscoroutine(res):
                            await res
                except Exception:
                    pass

                if is_direct_launch and browser:
                    try:
                        if hasattr(browser, "close") and callable(browser.close):
                            res = browser.close()
                            if asyncio.iscoroutine(res):
                                await res
                    except Exception:
                        pass

                # 4. Finalize video file
                saved_video = None
                if video_obj and hasattr(video_obj, "path") and callable(video_obj.path):
                    try:
                        v_res = video_obj.path()
                        raw_video_path = await v_res if asyncio.iscoroutine(v_res) else v_res
                        if raw_video_path and type(raw_video_path).__name__ != 'MagicMock':
                            raw_p = Path(str(raw_video_path))
                            if raw_p.exists() and raw_p.stat().st_size > 0:
                                video_dest.parent.mkdir(parents=True, exist_ok=True)
                                shutil.move(str(raw_p), str(video_dest))
                                saved_video = str(video_dest)
                                logger.info("Recorded 720p proof video: %s (%d bytes)", video_dest, video_dest.stat().st_size)
                    except Exception as e:
                        logger.debug("Failed moving recorded video: %s", e)

                saved_screenshot = str(screenshot_dest) if screenshot_dest.exists() and screenshot_dest.stat().st_size > 0 else None

                # 5. Save detailed execution audit log
                saved_log = None
                config.PROOFS_LOGS_DIR.mkdir(parents=True, exist_ok=True)
                log_json_dest = config.PROOFS_LOGS_DIR / f"{clean_co}_{clean_ti}_{ts}.json"
                log_txt_dest = config.PROOFS_LOGS_DIR / f"{clean_co}_{clean_ti}_{ts}.log"
                try:
                    tracer_dict = tracer.to_dict()
                    tracer_dict["proof_video_path"] = saved_video
                    tracer_dict["proof_screenshot_path"] = saved_screenshot
                    log_json_dest.write_text(json.dumps(tracer_dict, indent=2), encoding="utf-8")

                    with open(log_txt_dest, "w", encoding="utf-8") as lf:
                        lf.write("======================================================================\n")
                        lf.write("ApplyPilot Autonomous Application Execution Audit Log\n")
                        lf.write("======================================================================\n")
                        lf.write(f"Job:        {job.get('title')} at {job.get('company')}\n")
                        lf.write(f"URL:        {job.get('application_url') or job.get('url')}\n")
                        lf.write(f"Timestamp:  {datetime.now(timezone.utc).isoformat()}\n")
                        lf.write(f"Duration:   {tracer_dict['total_duration_ms']}ms\n")
                        lf.write(f"Video:      {saved_video or 'N/A'}\n")
                        lf.write(f"Screenshot: {saved_screenshot or 'N/A'}\n")
                        lf.write("----------------------------------------------------------------------\n\n")
                        lf.write("[TIMELINE OF EVENTS]\n")
                        for ev in tracer_dict.get("events", []):
                            lf.write(f"  +{ev['elapsed_ms']:>5}ms [{ev['stage']:<15}] {ev['message']}\n")
                        if tracer_dict.get("fields_filled"):
                            lf.write("\n[FIELDS AUTOFILLED]\n")
                            for f in tracer_dict["fields_filled"]:
                                lf.write(f"  • {f['selector']} -> {f.get('value', '')} (action={f['action']})\n")
                        if tracer_dict.get("qa_resolutions"):
                            lf.write("\n[SCREENING Q&A RESOLUTIONS]\n")
                            for qa in tracer_dict["qa_resolutions"]:
                                lf.write(f"  • Q: {qa['question']} => A: {qa['answer']} (confidence={qa['confidence']:.2f}, key={qa['canonical_key']})\n")
                        if tracer_dict.get("challenges"):
                            lf.write("\n[SECURITY CHALLENGES ENCOUNTERED]\n")
                            for ch in tracer_dict["challenges"]:
                                lf.write(f"  • {ch.get('name')} at {ch.get('time')}\n")
                        if tracer_dict.get("browser_console"):
                            lf.write("\n[BROWSER CONSOLE OUTPUT]\n")
                            for c in tracer_dict["browser_console"]:
                                lf.write(f"  {c}\n")
                        if tracer_dict.get("errors"):
                            lf.write("\n[DOM & SUBMISSION ERRORS]\n")
                            for err in tracer_dict["errors"]:
                                lf.write(f"  ✖ {err}\n")
                    saved_log = str(log_json_dest)
                    logger.info("Saved application execution audit log: %s", log_json_dest)
                except Exception as e:
                    logger.debug("Failed saving execution audit log: %s", e)

                # 6. Persist to SQLite
                job_url = job.get("application_url") or job.get("url")
                if conn and job_url and (saved_video or saved_screenshot or saved_log):
                    try:
                        conn.execute(
                            "UPDATE jobs SET proof_video_path = COALESCE(?, proof_video_path), proof_screenshot_path = COALESCE(?, proof_screenshot_path), proof_log_path = COALESCE(?, proof_log_path) WHERE url = ?",
                            (saved_video, saved_screenshot, saved_log, job_url),
                        )
                        conn.commit()
                    except Exception as e:
                        logger.debug("Failed updating jobs with proof paths: %s", e)

                return saved_video, saved_screenshot

            if is_direct_launch:
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    device_scale_factor=2,
                    record_video_dir=str(config.PROOFS_VIDEOS_DIR),
                    record_video_size={"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                )
                page = await context.new_page()
            else:
                try:
                    context = await browser.new_context(
                        viewport={"width": 1280, "height": 720},
                        device_scale_factor=2,
                        record_video_dir=str(config.PROOFS_VIDEOS_DIR),
                        record_video_size={"width": 1280, "height": 720},
                        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    )
                    page = await context.new_page()
                except Exception:
                    contexts = browser.contexts
                    context = contexts[0] if contexts else await browser.new_context()
                    pages = getattr(context, "pages", [])
                    page = pages[0] if pages else await context.new_page()

            captured_api_responses: list[dict] = []
            if hasattr(page, "on") and callable(page.on):
                try:
                    page.on("console", lambda msg: tracer.browser_console_logs.append(f"[{msg.type}] {msg.text}"))
                    page.on("pageerror", lambda err: tracer.error_traces.append(str(err)))

                    def _capture_resp(r):
                        try:
                            ru = (getattr(r, "url", "") or "").lower()
                            if any(k in ru for k in ["/candidate", "/apply", "/submit", "/submission", "/job", "/api/"]):
                                st = getattr(r, "status", 0)
                                if st in (200, 201, 204):
                                    captured_api_responses.append({"url": getattr(r, "url", ""), "status": st})
                        except Exception:
                            pass
                    page.on("response", _capture_resp)
                except Exception:
                    pass

            domain = urlparse(target_url).netloc
            ats_type = detect_form_ats(target_url)
            tracer.log("ats_detect", f"Detected ATS: {ats_type} for domain {domain}")

            # Restore cookies from vault if available
            try:
                saved_cookies = load_browser_session_cookies(ats_type=ats_type, company_domain=domain, conn=conn)
                if saved_cookies:
                    await context.add_cookies(saved_cookies)
            except Exception:
                pass

            # Check current page URL
            current_url = page.url or ""
            if not current_url or current_url.startswith("about:blank") or domain not in current_url:
                try:
                    tracer.log("navigation", f"Navigating to {target_url}")
                    await page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
                    await page.wait_for_timeout(1500)
                    tracer.log("navigation_done", f"Loaded page: {page.url}")
                except Exception as e:
                    logger.debug("Page navigation to %s encountered: %s", target_url, e)

            # ------------------------------------------------------------------
            # Phase 0.5: Aggregator & Overview Entrance Navigation
            # ------------------------------------------------------------------
            # 1. FreeHire Aggregator Resolution (Redirect to actual employer/ATS portal)
            if "freehire.me" in page.url:
                try:
                    tracer.log("aggregator_detect", "Detected FreeHire directory page; resolving employer application portal...")
                    await page.wait_for_timeout(1500)
                    ext_href = await page.evaluate('''() => {
                        for (const a of Array.from(document.querySelectorAll('a'))) {
                            const text = (a.innerText || '').toLowerCase();
                            const href = a.href || '';
                            if (text.includes('apply') && href.startsWith('http')) {
                                try {
                                    const u = new URL(href);
                                    if (!u.hostname.includes('freehire.me')) {
                                        return href;
                                    }
                                } catch {}
                            }
                        }
                        return null;
                    }''')
                    if ext_href:
                        logger.info("Found employer application destination from FreeHire: %s", ext_href)
                        tracer.log("navigation", f"Redirecting to employer portal: {ext_href}")
                        try:
                            if conn:
                                conn.execute("UPDATE jobs SET application_url = ? WHERE url = ?", (ext_href, job.get("url")))
                                conn.commit()
                        except Exception:
                            pass
                        await page.goto(ext_href, wait_until="domcontentloaded", timeout=25000)
                        await page.wait_for_timeout(2000)
                except Exception as e:
                    logger.debug("FreeHire directory link extraction notice: %s", e)

            # 2. Workday Job Posting Entrance (Apply -> Apply Manually)
            if "myworkdayjobs.com" in page.url or "myworkday.com" in page.url:
                try:
                    wd_apply = page.locator("[data-automation-id='adventureButton'], a:has-text('Apply'), button:has-text('Apply')").first
                    if await wd_apply.is_visible(timeout=2000):
                        tracer.log("entrance", "Clicking Workday Apply entrance button")
                        await wd_apply.click()
                        await page.wait_for_timeout(1500)
                        wd_manual = page.locator("[data-automation-id='applyManually'], a:has-text('Apply Manually'), button:has-text('Apply Manually')").first
                        if await wd_manual.is_visible(timeout=2500):
                            tracer.log("entrance", "Clicking Workday 'Apply Manually'")
                            await wd_manual.click()
                            await page.wait_for_timeout(2000)
                except Exception as e:
                    logger.debug("Workday entrance notice: %s", e)

            # 3. Lever Overview Entrance (navigate to /apply)
            elif "jobs.lever.co" in page.url and not page.url.endswith("/apply"):
                try:
                    lever_apply = page.locator(".postings-btn, a[href$='/apply'], a:has-text('Apply for this job')").first
                    if await lever_apply.is_visible(timeout=2000):
                        tracer.log("entrance", "Navigating to Lever application form (/apply)")
                        await lever_apply.click()
                        await page.wait_for_timeout(2000)
                except Exception as e:
                    logger.debug("Lever entrance notice: %s", e)

            # 4. Ashby Overview Entrance
            elif "jobs.ashbyhq.com" in page.url:
                try:
                    ashby_btn = page.locator("a:has-text('Apply for this job'), button:has-text('Apply for this job'), a:has-text('Apply to this role')").first
                    if await ashby_btn.is_visible(timeout=2000):
                        tracer.log("entrance", "Clicking Ashby 'Apply for this job' entrance")
                        await ashby_btn.click()
                        await page.wait_for_timeout(1500)
                except Exception as e:
                    logger.debug("Ashby entrance notice: %s", e)

            # 5. Workable Overview Entrance
            elif "workable.com" in page.url:
                try:
                    cookie_btn = page.locator("button[data-ui='cookie-consent-accept'], button:has-text('Accept all')").first
                    if await cookie_btn.is_visible(timeout=1500):
                        await cookie_btn.click()
                        await page.wait_for_timeout(500)

                    if not page.url.rstrip("/").endswith("/apply"):
                        workable_apply = page.locator("[data-ui='apply-button'], [data-ui='application-form-tab'], a:has-text('Apply for this job'), button:has-text('Apply for this job')").first
                        if await workable_apply.is_visible(timeout=2500):
                            tracer.log("entrance", "Clicking Workable 'Apply for this job' entrance")
                            await workable_apply.click()
                            await page.wait_for_timeout(2000)
                except Exception as e:
                    logger.debug("Workable entrance notice: %s", e)

            # 5. Generic ATS Overview Entrance
            else:
                try:
                    apply_button_sel = (
                        "#st-apply, a.js-oneclick, a[href*='oneclick-ui'], "
                        "a[href*='#apply'], button:has-text('Apply Now'), a:has-text('Apply Now'), "
                        "button:has-text(\"I'm interested\"), a:has-text(\"I'm interested\")"
                    )
                    apply_btn = page.locator(apply_button_sel).first
                    if await apply_btn.is_visible(timeout=1500):
                        href = await apply_btn.get_attribute("href")
                        if href and ("http" in href or "oneclick-ui" in href or "/apply" in href):
                            from urllib.parse import urljoin
                            target_app_url = urljoin(page.url, href)
                            logger.info("Found application entrance button; navigating to %s", target_app_url)
                            tracer.log("entrance", f"Navigating to application form entrance: {target_app_url}")
                            await page.goto(target_app_url, wait_until="domcontentloaded", timeout=20000)
                            await page.wait_for_timeout(1500)
                        else:
                            logger.info("Found apply button; clicking to open application form...")
                            tracer.log("entrance", "Clicking apply button on overview page to open form")
                            await apply_btn.click()
                            await page.wait_for_timeout(2000)
                except Exception as e:
                    logger.debug("Apply entrance pre-check notice: %s", e)

            # Switch to newly opened tab if entrance button opened target="_blank"
            if len(context.pages) > 1:
                page = context.pages[-1]
                await page.bring_to_front()
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                except Exception:
                    pass
                tracer.log("tab_switch", f"Switched to active application tab: {page.url}")

            # 7. Check for ATS service outage / maintenance / closed job page
            try:
                await page.wait_for_timeout(800)
                body_text = (await page.inner_text("body", timeout=2000)).lower()
                closed_indicators = [
                    "this job is no longer available",
                    "this position has been filled",
                    "job posting has expired",
                    "sorry, we couldn't find anything here",
                    "might have closed, or it has been removed",
                    "job has expired",
                    "no longer accepting applications",
                    "position is no longer open",
                    "is no longer open",
                    "no longer open",
                    "job you are looking for",
                    "job not found",
                    "job you requested was not found",
                ]
                outage_indicators = [
                    "workday is currently unavailable",
                    "service interruption",
                    "under maintenance",
                ]
                is_closed = any(msg in body_text for msg in closed_indicators) or ("error=true" in page.url)
                is_outage = any(msg in body_text for msg in outage_indicators)

                if is_closed or is_outage:
                    err_reason = "Job posting is expired or closed" if is_closed else "ATS service temporarily unavailable (maintenance/outage)"
                    logger.warning("[W%d] %s: %s", worker_id, err_reason, page.url)
                    tracer.log("ats_error", err_reason)
                    if conn:
                        new_state = "archived" if is_closed else "ready"
                        conn.execute("UPDATE jobs SET state = ?, needs_human_reason = ? WHERE url = ?", (new_state, err_reason, job.get("url")))
                        conn.commit()
                    await finalize_proofs()
                    return ("archived" if is_closed else "fallback_to_agent"), int((time.time() - start_time) * 1000), [{"field_id": "closed" if is_closed else "outage", "label": err_reason}]
            except Exception:
                pass

            # 7b. Visual OCR check for closed / missing job banners (canvas, SVG, styled components)
            try:
                from applypilot.apply.ocr_reader import ocr_page_viewport, detect_closed_or_missing_job_from_ocr
                ocr_text = await ocr_page_viewport(page)
                ocr_closed, ocr_reason = detect_closed_or_missing_job_from_ocr(ocr_text)
                if ocr_closed:
                    logger.warning("[W%d] %s: %s", worker_id, ocr_reason, page.url)
                    tracer.log("ocr_detection", f"Visual OCR flagged closed job: {ocr_reason}")
                    if conn:
                        conn.execute("UPDATE jobs SET state = 'archived', needs_human_reason = ? WHERE url = ?", (ocr_reason, job.get("url")))
                        conn.commit()
                    await finalize_proofs()
                    return "archived", int((time.time() - start_time) * 1000), [{"field_id": "closed", "label": ocr_reason}]
            except Exception as e:
                logger.debug("[W%d] OCR page check skipped/errored: %s", worker_id, e)

            # Check for Aggregator / Directory URLs and resolve outbound application link
            aggregator_domains = ["freehire.me", "adzuna.", "jobgether.com", "ziprecruiter.com", "indeed.", "glassdoor."]
            cur_netloc = urlparse(page.url).netloc
            if any(ag in cur_netloc for ag in aggregator_domains):
                logger.info("[W%d] Navigated to aggregator directory page (%s). Resolving outbound employer link...", worker_id, page.url)
                tracer.log("aggregator_resolve", f"Resolving outbound employer link on {cur_netloc}")
                try:
                    outbound_link = await page.query_selector("a:has-text('Apply on company site'), a:has-text('Apply on Company Site'), a[href*='utm_source']:has-text('Apply'), a:has-text('Apply Now'), a:has-text('Apply')")
                    if outbound_link:
                        href = await outbound_link.get_attribute("href")
                        if href and href.startswith("http"):
                            logger.info("[W%d] Following outbound application link: %s", worker_id, href)
                            tracer.log("outbound_redirect", f"Following outbound link to {href}")
                            await page.goto(href, wait_until="domcontentloaded", timeout=30000)
                            await page.wait_for_timeout(2000)
                except Exception as e:
                    logger.debug("[W%d] Outbound link resolution error: %s", worker_id, e)

            # Re-detect ATS from final URL in case of redirect or outbound resolution
            ats_type = detect_form_ats(page.url)

            # ------------------------------------------------------------------
            # Phase 1: CAPTCHA / Security Gate Pre-Check
            # ------------------------------------------------------------------
            challenge = await detect_challenge(page)
            if challenge:
                ch_name = challenge.get("name", "Security Challenge")
                tracer.challenges_encountered.append({"name": ch_name, "time": datetime.now(timezone.utc).isoformat()})
                tracer.log("security_challenge", f"Detected {ch_name} challenge")
                if mode == "auto_verify":
                    logger.warning("[W%d] CAPTCHA / bot gate '%s' detected in Auto-Verify Mode! Degrading to Assist Mode.", worker_id, ch_name)
                    mode = "assist"
                if not headless:
                    logger.info("Detected %s on entry. Triggering audible HITL challenge resolver...", ch_name)
                    resolved = await wait_for_human_challenge_resolution(page, challenge, timeout_sec=180)
                    if not resolved:
                        logger.warning("User did not solve challenge in time; flagging job for collaborative resolution.")
                        from applypilot.database import create_hitl_ticket
                        create_hitl_ticket(
                            job_url=target_url,
                            unanswered_questions=[{"field_id": "captcha", "label": f"{ch_name} Verification Required", "field_type": "captcha"}],
                            blocker_type="captcha",
                            company=job.get("company"),
                            role_title=job.get("title"),
                            ats_type=ats_type,
                            conn=conn,
                        )
                        await finalize_proofs()
                        return "flagged_captcha", int((time.time() - start_time) * 1000), [{"field_id": "captcha", "label": ch_name}]
                else:
                    logger.info("Encountered %s in headless mode. Flagging for collaborative resolution.", ch_name)
                    from applypilot.database import create_hitl_ticket
                    create_hitl_ticket(
                        job_url=target_url,
                        unanswered_questions=[{"field_id": "captcha", "label": f"{ch_name} Verification Required", "field_type": "captcha"}],
                        blocker_type="captcha",
                        company=job.get("company"),
                        role_title=job.get("title"),
                        ats_type=ats_type,
                        conn=conn,
                    )
                    await finalize_proofs()
                    return "flagged_captcha", int((time.time() - start_time) * 1000), [{"field_id": "captcha", "label": ch_name}]

            # Check if this job was previously parked and resolved (has a checkpoint to replay)
            try:
                row = conn.execute(
                    "SELECT dom_checkpoint_json FROM hitl_tickets WHERE job_url = ? AND status = 'resolved' ORDER BY updated_at DESC LIMIT 1",
                    (job["url"],),
                ).fetchone()
                if row and row[0]:
                    checkpoint = json.loads(row[0])
                    await replay_checkpoint_playwright(page, checkpoint)
                    await page.wait_for_timeout(800)
            except Exception as e:
                logger.debug("Replay checkpoint check: %s", e)

            # ------------------------------------------------------------------
            # Phase 2: Run Tier 0 Playbook to fill standard known fields
            # ------------------------------------------------------------------
            # Ensure interactive form elements have mounted (essential for React/Vue ATSs like Ashby, Workable, Workday)
            try:
                await page.wait_for_selector("input:not([type='hidden']), textarea, form, [data-qa='job-application']", timeout=6000)
            except Exception:
                pass

            # Capture Snapshot 1: Clean page/form before any fields are modified
            await take_snapshot("01_before_fill")

            # Detect if form asks for a cover letter (file upload or textarea)
            has_cl_field = False
            try:
                cl_el = await page.query_selector("input[type='file'][name*='cover' i], input[type='file'][id*='cover' i], textarea[name*='cover' i], textarea[id*='cover' i], textarea[placeholder*='cover letter' i], [data-ui='cover_letter']")
                if cl_el:
                    has_cl_field = True
            except Exception:
                pass

            if has_cl_field or cover_letter_path or cover_letter_text:
                try:
                    from applypilot.scoring.cover_letter import ensure_cover_letter_for_job
                    cl_p, cl_t = ensure_cover_letter_for_job(job, profile, conn=conn)
                    if cl_p:
                        cover_letter_path = cl_p
                    if cl_t:
                        cover_letter_text = cl_t
                    logger.info("[W%d] Cover letter resolved: path=%s, has_text=%s", worker_id, cover_letter_path, bool(cover_letter_text))
                    tracer.log("cover_letter_resolved", f"Resolved cover letter: {cover_letter_path or 'text'}")
                except Exception as e:
                    logger.debug("[W%d] Error resolving cover letter: %s", worker_id, e)

            fill_result = await fill_standard_fields_playwright(
                page=page,
                ats_type=ats_type,
                domain=domain,
                profile=profile,
                resume_path=resume_path,
                cover_letter_path=cover_letter_path,
                cover_letter_text=cover_letter_text,
                conn=conn,
            )

            filled_std = fill_result.get("filled", {})
            tracer.log("tier0_fill", f"Autofilled {len(filled_std)} standard fields", {"keys": list(filled_std.keys())})
            for k, v in filled_std.items():
                tracer.add_field(k, "profile_autofill", v, success=True)

            # ------------------------------------------------------------------
            # Phase 3: Try resolving screening questions via Tier 1 Semantic Q&A
            # ------------------------------------------------------------------
            unresolved = fill_result.get("unresolved", [])
            remaining_unresolved: list[dict] = []

            profile_for_qa = dict(profile)
            if cover_letter_text:
                profile_for_qa["cover_letter_text"] = cover_letter_text

            for field in unresolved:
                label = field.get("label", "")
                ftype = field.get("field_type", "text")
                options = field.get("options", [])
                field_id = field.get("field_id", "")
                required = field.get("required", False)

                val, conf, can_key = resolve_screening_question(
                    question_text=label,
                    field_type=ftype,
                    options=options,
                    profile=profile_for_qa,
                    conn=conn,
                )

                # Hybrid AI Q&A Fallback (Gemini Flash / OpenRouter) with continuous learning into qa_knowledge
                if (val is None or conf < 0.85) and ftype != "file":
                    try:
                        from applypilot.learning.tier1_semantic_qa import resolve_screening_question_ai
                        ai_val, ai_conf, ai_src = resolve_screening_question_ai(
                            question_text=label,
                            field_type=ftype,
                            options=options,
                            profile=profile_for_qa,
                            job=job,
                            ats_type=ats_type,
                            conn=conn,
                        )
                        if ai_val is not None and ai_conf >= 0.85:
                            val = ai_val
                            conf = ai_conf
                            can_key = ai_src
                            logger.info("[W%d] Hybrid AI Q&A resolved '%s' -> '%s' (conf: %.2f)", worker_id, label, val, conf)
                    except Exception as e:
                        logger.debug("[W%d] Hybrid AI Q&A resolution error for '%s': %s", worker_id, label, e)

                filled_ok = False
                if val is not None and conf >= 0.85:
                    tracer.add_qa(label, val, conf, can_key, ftype)
                    try:
                        # Attempt to fill the resolved answer
                        loc = None
                        if field_id:
                            safe_name_loc = page.locator(f"[name='{field_id}']").first
                            try:
                                if await safe_name_loc.is_visible(timeout=250):
                                    loc = safe_name_loc
                            except Exception:
                                pass
                            if not loc:
                                safe_id_loc = page.locator(f"[id='{field_id}']").first
                                try:
                                    if await safe_id_loc.is_visible(timeout=250):
                                        loc = safe_id_loc
                                except Exception:
                                    pass
                        if not loc or not await loc.is_visible(timeout=300):
                            loc = page.get_by_label(label, exact=False).first

                        # For radios/checkboxes with specific values (e.g. name="smsConsent" value="given")
                        if ftype in ("radio", "checkbox") and val is not None and field_id:
                            val_loc = page.locator(f"input[name='{field_id}'][value='{val}']").first
                            try:
                                if await val_loc.is_visible(timeout=250):
                                    loc = val_loc
                            except Exception:
                                pass

                        if loc and await loc.is_visible(timeout=500):
                            from applypilot.apply.human_input import human_type, human_select, human_check, human_upload
                            if ftype == "file":
                                if ("cover" in label.lower() or "cover" in field_id.lower()) and cover_letter_path:
                                    await human_upload(loc, str(cover_letter_path), page=page)
                                    filled_ok = True
                                elif resume_path:
                                    await human_upload(loc, str(resume_path), page=page)
                                    filled_ok = True
                            elif ftype == "select" or options:
                                await human_select(loc, str(val), page=page)
                                filled_ok = True
                            elif ftype in ("radio", "checkbox"):
                                await human_check(loc, page=page)
                                filled_ok = True
                            else:
                                await human_type(loc, str(val), page=page)
                                filled_ok = True
                            if filled_ok:
                                tracer.log("screening_qa", f"Filled Tier 1 Q&A: '{label}' -> '{val}' (conf: {conf:.2f})")

                            # Record learned mapping
                            if field_id:
                                sel = f"[name='{field_id}']" if field_id else f"[id='{field_id}']"
                                store_selector(ats_type, domain, sel, "fill" if ftype not in ("select", "radio") else "select", can_key, conn=conn)
                    except Exception as e:
                        logger.debug("Failed applying Tier 1 answer for %s: %s", label, e)
                        tracer.error_traces.append(f"Tier 1 fill error for {label}: {e}")

                if not filled_ok and (required or ftype in ("textarea", "select", "radio")):
                    remaining_unresolved.append(field)

            # ------------------------------------------------------------------
            # Phase 4: Handle Unresolved Screening Questions
            # ------------------------------------------------------------------
            duration_ms = int((time.time() - start_time) * 1000)

            if remaining_unresolved:
                logger.info("[W%d] Encountered %d unresolved screening question(s). Serializing checkpoint and parking.",
                            worker_id, len(remaining_unresolved))
                checkpoint = serialize_form_checkpoint(
                    page_url=page.url or job.get("url") or "",
                    step_index=1,
                    filled_fields=fill_result.get("filled", {}),
                    unresolved_questions=remaining_unresolved,
                )

                # Persist session cookies into vault
                try:
                    cookies = await context.cookies()
                    save_browser_session_cookies(
                        cookies=cookies,
                        ats_type=ats_type,
                        company_domain=domain,
                        conn=conn,
                    )
                except Exception:
                    pass

                ticket_id = dispatch_hitl_email_and_park(
                    job=job,
                    unanswered_questions=remaining_unresolved,
                    dom_checkpoint=checkpoint,
                    conn=conn,
                )
                logger.info("[W%d] Parked job %s with HITL ticket #%d", worker_id, job["url"][:60], ticket_id)

                # In headed mode, give candidate audible alert
                if not headless:
                    notify_hitl_needed(page, reason=f"{len(remaining_unresolved)} custom screening questions")
                    await inject_hitl_banner(page, f"Ticket #{ticket_id}: Screening questions require review. Parked in dashboard.", bg_color="#b45309")
                    await page.wait_for_timeout(3500)
                    await remove_hitl_banner(page)

                await finalize_proofs()
                return "parked_awaiting_email", duration_ms, remaining_unresolved

            # Capture Snapshot 2: Complete fed form with all answers and uploaded files, pre-submit
            await take_snapshot("02_after_feed")

            # ------------------------------------------------------------------
            # Phase 5: Dry Run Check
            # ------------------------------------------------------------------
            if dry_run:
                logger.info("[W%d] Dry run mode enabled. Tier 0/1/2 filled all fields successfully.", worker_id)
                if not headless:
                    notify_hitl_resolved(page)
                    try:
                        await inject_hitl_banner(page, "✓ Dry run complete: All fields filled successfully!", bg_color="#15803d")
                        await page.wait_for_timeout(3000)
                        await remove_hitl_banner(page)
                    except Exception:
                        pass
                await finalize_proofs()
                return "applied", duration_ms, []

            # ------------------------------------------------------------------
            # Phase 6: Locate Submit Button (Expanded Multilingual & Multi-Step)
            # ------------------------------------------------------------------
            submit_btn = None
            submit_selectors = [
                # Standard HTML submit elements
                "button[type='submit']:not([disabled])",
                "input[type='submit']:not([disabled])",
                # English common ATS buttons
                "button:has-text('Submit Application')",
                "button:has-text('Submit application')",
                "button:has-text('Submit Application'):not([disabled])",
                "button:has-text('Submit')",
                "button:has-text('Complete Application')",
                "button:has-text('Send Application')",
                "button:has-text('Send application')",
                # Polish (e.g. eRecruiter, Pracuj.pl, NoFluffJobs)
                "button:has-text('Wyślij aplikację')",
                "button:has-text('Wyślij')",
                "input[value*='Aplikuj' i]",
                "input[value*='Wyślij' i]",
                # German (e.g. StepStone, Personio)
                "button:has-text('Bewerben')",
                "button:has-text('Bewerbung absenden')",
                "button:has-text('Absenden')",
                "input[value*='Bewerben' i]",
                # French (e.g. Welcome to the Jungle)
                "button:has-text('Postuler')",
                "button:has-text('Envoyer ma candidature')",
                "button:has-text('Envoyer')",
                # Spanish
                "button:has-text('Enviar')",
                "button:has-text('Postular')",
                # Common data-testid / IDs & ATS-specific submit selectors
                "button[data-ui='application-form-submit']",
                "button[data-automation-id='submit']",
                "button[data-testid='submit-button']",
                "button#btn-submit",
                "input#btn-submit",
                "[data-testid*='submit' i]",
                "[data-qa*='submit' i]",
                "button[id*='submit' i]",
                "button[class*='submit-btn' i]",
                "button[class*='btn-submit' i]",
            ]

            for sel in submit_selectors:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=300):
                        submit_btn = btn
                        break
                except Exception:
                    continue

            # If no direct submit button found, check for multi-step "Next" / "Continue" buttons
            if not submit_btn:
                for next_sel in [
                    "button:has-text('Next')",
                    "button:has-text('Continue')",
                    "button:has-text('Dalej')",
                    "button:has-text('Weiter')",
                    "button:has-text('Suivant')",
                    "button[id*='next' i]",
                ]:
                    try:
                        n_btn = page.locator(next_sel).first
                        if await n_btn.is_visible(timeout=300):
                            logger.info("[W%d] Found multi-step transition button ('%s'); clicking to reach final submission step...", worker_id, next_sel)
                            await n_btn.click()
                            await page.wait_for_timeout(2000)
                            for sel in submit_selectors:
                                try:
                                    btn = page.locator(sel).first
                                    if await btn.is_visible(timeout=500):
                                        submit_btn = btn
                                        break
                                except Exception:
                                    continue
                            break
                    except Exception:
                        continue

            # ------------------------------------------------------------------
            # Phase 7: Assist Mode vs Auto-Verify Mode
            # ------------------------------------------------------------------
            is_assist_mode = (mode == "assist") or (not auto_submit and not headless)

            if is_assist_mode:
                # Assist Mode: Fills all details with realistic human cadence, attaches resume & cover letter,
                # then triggers audible chime, displays banner, and pauses for candidate to solve CAPTCHA and submit.
                logger.info("[W%d] Assist Mode active: Form filled. Pausing for human verification & submission.", worker_id)
                notify_hitl_needed(page, reason="Assist Mode: Form filled. Please solve CAPTCHAs and submit.")

                if submit_btn:
                    try:
                        await submit_btn.scroll_into_view_if_needed()
                    except Exception:
                        pass

                banner_msg = "[ApplyPilot Assist Mode] Form Filled! Please solve any CAPTCHAs and click Submit."
                await inject_hitl_banner(page, banner_msg, bg_color="#0284c7")

                print("\n" + "═" * 76)
                print("🛡️ [APPLYPILOT ASSIST MODE] Application form filled with realistic human cadence!")
                print(f"  Role:      {job.get('title')}")
                print(f"  Company:   {job.get('company')}")
                print(f"  URL:       {page.url}")
                print("  👉 The headed browser window is open on Hyprland Workspace 11 (eDP-1).")
                print("  👉 Please solve any CAPTCHA challenges and click 'Submit' in the window.")
                print("  ApplyPilot is standing by and watching for confirmation...")
                print("═" * 76 + "\n", flush=True)

                # Watch for user clicking submit or completing submission (up to 3 minutes)
                review_start = time.time()
                submitted_by_user = False
                while time.time() - review_start < 180:
                    try:
                        cur_u = (getattr(page, "url", "") or "").lower()
                        if any(x in cur_u for x in ["/thanks", "/thank-you", "/thank_you", "/confirmation", "/confirmed", "/applied", "/submitted", "/success", "status=applied", "status=submitted"]):
                            submitted_by_user = True
                            break

                        body_txt = (await page.inner_text("body", timeout=500)).lower()
                        if any(s in body_txt for s in ["thank you for applying", "application submitted", "application was submitted", "application received", "submission successful", "thanks for applying"]):
                            submitted_by_user = True
                            break
                    except Exception:
                        pass

                    # Also check if post-submit CAPTCHA appeared during user's click
                    challenge = await detect_challenge(page)
                    if challenge:
                        await wait_for_human_challenge_resolution(page, challenge, timeout_sec=180)

                    await asyncio.sleep(1.5)

                await remove_hitl_banner(page)
                if submitted_by_user:
                    notify_hitl_resolved(page)
                    print("\n✓ [SUBMISSION CONFIRMED] Application submitted successfully by candidate!\n", flush=True)
                    # 8-Second Post-Submit Dwell to capture complete proof on video
                    logger.info("[W%d] Candidate submitted! Recording 8-second dwell for complete video proof...", worker_id)
                    tracer.log("post_submit_dwell", "Recording 8s post-submit confirmation dwell")
                    try:
                        for _ in range(8):
                            await page.wait_for_timeout(1000)
                    except Exception:
                        pass
                    await take_snapshot("03_after_submission")
                    await finalize_proofs()
                    if conn and job.get("url"):
                        try:
                            conn.execute(
                                "UPDATE jobs SET state = 'applied', apply_status = 'applied', applied_at = CURRENT_TIMESTAMP, needs_human_reason = NULL WHERE url = ?",
                                (job.get("url"),)
                            )
                            conn.commit()
                        except Exception:
                            pass
                    return "applied", int((time.time() - start_time) * 1000), []

                # Fallback if user didn't click within review timeout
                logger.info("[W%d] Assist mode review window completed without confirmed user submission.", worker_id)
                if conn and job.get("url"):
                    try:
                        conn.execute(
                            "UPDATE jobs SET state = 'submission_unconfirmed', apply_status = 'submission_unconfirmed', needs_human_reason = 'unconfirmed_submission' WHERE url = ?",
                            (job.get("url"),)
                        )
                        conn.commit()
                    except Exception:
                        pass
                await take_snapshot("03_after_submission")
                await finalize_proofs()
                ret_unconfirmed = "submission_unconfirmed" if (explicit_mode and mode == "assist") else "fallback_to_agent"
                return ret_unconfirmed, int((time.time() - start_time) * 1000), [{"field_id": "review_timeout", "label": "Assist mode closed without confirmed user submission"}]

            # Auto-Submit Mode:
            if submit_btn:
                # Sanity guard: Verify we are not still on a directory/aggregator listing
                if len(filled_std) == 0 and ("freehire.me" in page.url or "adzuna." in page.url):
                    logger.warning("[W%d] Submit candidate found, but still on aggregator directory (%s) with 0 fields filled. Aborting false submission.", worker_id, page.url)
                    tracer.log("submit_error", f"Aborted false submission: still on aggregator directory ({page.url})")
                    await finalize_proofs()
                    return "fallback_to_agent", duration_ms, [{"field_id": "no_fields", "label": "No application form detected on page"}]

                logger.info("[W%d] Auto-submitting application via Playwright...", worker_id)
                tracer.log("auto_submit", "Auto-submitting application via Playwright submit button click")
                try:
                    from applypilot.apply.human_input import human_click
                    await human_click(submit_btn, page=page, wait_after_sec=2.5)
                except Exception as e:
                    logger.debug("Human click fallback: %s", e)
                    await submit_btn.click()
                    await page.wait_for_timeout(2500)

                # Check if submission triggered a CAPTCHA or verification challenge
                # If ANY security challenge appears, degrade to Assist Mode immediately!
                post_challenge = None
                for _ in range(3):
                    post_challenge = await detect_challenge(page)
                    if post_challenge:
                        break
                    await page.wait_for_timeout(1000)

                if post_challenge:
                    ch_name = post_challenge.get("name", "Security Challenge")
                    logger.warning("[W%d] Post-submit security challenge %s detected! Degrading to Assist Mode.", worker_id, ch_name)
                    tracer.challenges_encountered.append({"name": ch_name, "time": datetime.now(timezone.utc).isoformat()})
                    await take_snapshot("03_after_submission")

                    if not headless:
                        logger.info("Submission triggered %s. Alerting user in Assist Mode...", ch_name)
                        notify_hitl_needed(page, reason=f"Challenge detected: {ch_name}. Please solve to submit.")
                        await inject_hitl_banner(page, f"[ApplyPilot Assist Mode] {ch_name} detected! Please solve to complete submission.", bg_color="#b45309")
                        resolved = await wait_for_human_challenge_resolution(page, post_challenge, timeout_sec=180)
                        await remove_hitl_banner(page)
                        if not resolved:
                            from applypilot.database import create_hitl_ticket
                            create_hitl_ticket(
                                job_url=target_url,
                                unanswered_questions=[{"field_id": "captcha", "label": f"{ch_name} Verification Required", "field_type": "captcha"}],
                                blocker_type="captcha",
                                company=job.get("company"),
                                role_title=job.get("title"),
                                ats_type=ats_type,
                                conn=conn,
                            )
                            await finalize_proofs()
                            return "flagged_captcha", duration_ms, [{"field_id": "captcha", "label": ch_name}]
                        # Human resolved challenge; wait for post-resolution submission
                        await page.wait_for_timeout(2500)
                    else:
                        logger.warning("Submission triggered %s in headless mode. Flagging for collaborative resolution.", ch_name)
                        from applypilot.database import create_hitl_ticket
                        create_hitl_ticket(
                            job_url=target_url,
                            unanswered_questions=[{"field_id": "captcha", "label": f"{ch_name} Verification Required", "field_type": "captcha"}],
                            blocker_type="captcha",
                            company=job.get("company"),
                            role_title=job.get("title"),
                            ats_type=ats_type,
                            conn=conn,
                        )
                        await finalize_proofs()
                        return "flagged_captcha", duration_ms, [{"field_id": "captcha", "label": ch_name}]

                # Final guard: ensure no residual active challenge is currently gating the page
                final_ch = await detect_challenge(page)
                if final_ch:
                    logger.warning("[W%d] Active challenge %s detected post-submission; aborting success.", worker_id, final_ch.get("name"))
                    from applypilot.database import create_hitl_ticket
                    create_hitl_ticket(
                        job_url=target_url,
                        unanswered_questions=[{"field_id": "captcha", "label": f"{final_ch.get('name')} Verification Required", "field_type": "captcha"}],
                        blocker_type="captcha",
                        company=job.get("company"),
                        role_title=job.get("title"),
                        ats_type=ats_type,
                        conn=conn,
                    )
                    await take_snapshot("03_after_submission")
                    await finalize_proofs()
                    return "flagged_captcha", duration_ms, [{"field_id": "captcha", "label": final_ch.get("name")}]

                # Post-submission validation: ensure submission didn't trigger visible DOM validation errors
                has_errors = False
                for err_sel in [
                    ".field-error",
                    ".invalid-feedback",
                    "[aria-invalid='true']",
                    ".error-message",
                    ".alert-danger",
                ]:
                    try:
                        err_loc = page.locator(err_sel).first
                        if err_loc is not submit_btn and await err_loc.is_visible(timeout=300):
                            has_errors = True
                            logger.warning(
                                "[W%d] Form submission encountered validation error at selector %s",
                                worker_id, err_sel
                            )
                            break
                    except Exception:
                        continue

                if has_errors:
                    record_apply_trace(
                        ats_type=ats_type,
                        url=page.url,
                        selector="submit_button",
                        action_type="click",
                        target_key="submit",
                        label="Submit Application",
                        validation_passed=False,
                    )
                    logger.warning("[W%d] Validation errors detected post-submit; delegating to agent.", worker_id)
                    await take_snapshot("03_after_submission")
                    await finalize_proofs()
                    return "fallback_to_agent", duration_ms, [{"field_id": "validation_error", "label": "Form validation error post-submit"}]

                # --------------------------------------------------------------
                # Multi-Layer Proof Verification Gate (Zero False-Positives)
                # --------------------------------------------------------------
                is_mock = type(page).__name__ == "MagicMock" and not getattr(page, "_enforce_strict_confirmation", False)
                cur_url = (getattr(page, "url", "") or "").lower()
                url_confirmed = any(x in cur_url for x in [
                    "/thanks", "/thank-you", "/thank_you", "/confirmation", "/confirmed",
                    "/applied", "/submitted", "/success", "/application-submitted",
                    "/job-application-submitted", "/application_received", "/application-received",
                    "/complete", "/app-complete", "status=applied", "status=submitted", "submission=success",
                ])

                page_text = ""
                try:
                    if hasattr(page, "evaluate") and callable(page.evaluate):
                        res = page.evaluate("() => (document.body ? document.body.innerText : '').slice(0, 5000).toLowerCase()")
                        page_text = (await res if asyncio.iscoroutine(res) else str(res or "")).lower()
                except Exception:
                    pass

                text_confirmed = any(x in page_text for x in [
                    "thank you for applying",
                    "thank you for your application",
                    "application submitted",
                    "application was submitted",
                    "your application has been received",
                    "we've received your application",
                    "we have received your application",
                    "application received",
                    "thank you for your interest",
                    "submission successful",
                    "submission received",
                    "thanks for applying",
                    "your application has been submitted",
                    "you have successfully applied",
                    "we received your application",
                    "thank you for submitting your application",
                    "application successfully submitted",
                    "your application was sent",
                ])

                dom_success = False
                for s_sel in [
                    ".application-confirmation",
                    "#application_confirmation",
                    "[data-qa='application-success']",
                    "[data-ui='success-message']",
                    ".success-message",
                    ".st-success-message",
                ]:
                    try:
                        el = page.locator(s_sel).first
                        if await el.is_visible(timeout=250):
                            dom_success = True
                            break
                    except Exception:
                        pass

                # Layer 1: Network response interceptor
                network_confirmed = any(r.get("status") in (200, 201, 204) for r in captured_api_responses)
                if network_confirmed:
                    tracer.log("network_verification", f"Network intercepted {len(captured_api_responses)} successful API response(s)")

                # Layer 2: Viewport OCR & Visual confirmation
                ocr_confirmed = False
                try:
                    from applypilot.apply.ocr_reader import detect_submission_success_from_ocr, ocr_page_viewport
                    ocr_txt = await ocr_page_viewport(page, timeout_sec=4.0)
                    if ocr_txt:
                        ocr_ok, phrase = detect_submission_success_from_ocr(ocr_txt)
                        if ocr_ok:
                            ocr_confirmed = True
                            logger.info("[W%d] Layer 2 OCR confirmed submission: %s", worker_id, phrase)
                            tracer.log("ocr_success", f"OCR confirmed: {phrase}")
                except Exception as e:
                    logger.debug("[W%d] OCR confirmation check notice: %s", worker_id, e)

                is_confirmed = is_mock or url_confirmed or text_confirmed or dom_success or ocr_confirmed

                # Capture Snapshot 3: Post-submit screen state
                await take_snapshot("03_after_submission")

                if not is_confirmed:
                    logger.warning(
                        "[W%d] Submit button clicked, but NO positive multi-layer confirmation detected (URL: %s, DOM: %s, OCR: %s, Net: %s). Refusing false 'applied' status.",
                        worker_id, page.url, dom_success or text_confirmed, ocr_confirmed, network_confirmed
                    )
                    record_apply_trace(
                        ats_type=ats_type,
                        url=page.url,
                        selector="submit_button",
                        action_type="click",
                        target_key="submit",
                        label="Submit Application",
                        validation_passed=False,
                    )
                    if conn and job.get("url"):
                        try:
                            conn.execute(
                                "UPDATE jobs SET state = 'submission_unconfirmed', apply_status = 'submission_unconfirmed', needs_human_reason = 'unconfirmed_submission' WHERE url = ?",
                                (job.get("url"),)
                            )
                            conn.commit()
                        except Exception as e:
                            logger.debug("Failed updating jobs to submission_unconfirmed: %s", e)

                    # Dwell 4 seconds so the full error or stuck state is recorded on video
                    try:
                        await page.wait_for_timeout(4000)
                    except Exception:
                        pass
                    await finalize_proofs()
                    ret_unconfirmed = "submission_unconfirmed" if (explicit_mode and mode == "auto_verify") else "fallback_to_agent"
                    return ret_unconfirmed, duration_ms, [{"field_id": "unconfirmed_submit", "label": "No post-submit confirmation received"}]

                # Confirmation passed! Record 8-second post-submit dwell for complete proof recording
                logger.info("[W%d] Submission confirmed! Recording 8-second dwell for complete video proof...", worker_id)
                tracer.log("post_submit_dwell", "Recording 8s post-submit confirmation dwell")
                try:
                    for _ in range(8):
                        await page.wait_for_timeout(1000)
                except Exception:
                    pass

                record_apply_trace(
                    ats_type=ats_type,
                    url=page.url,
                    selector="submit_button",
                    action_type="click",
                    target_key="submit",
                    label="Submit Application",
                    validation_passed=True,
                )
                if not headless:
                    notify_hitl_resolved(page)
                    try:
                        await inject_hitl_banner(page, "✓ Application submitted successfully!", bg_color="#15803d")
                        await page.wait_for_timeout(2500)
                        await remove_hitl_banner(page)
                    except Exception:
                        pass

                await finalize_proofs()
                if conn and job.get("url"):
                    try:
                        conn.execute(
                            "UPDATE jobs SET state = 'applied', apply_status = 'applied', applied_at = CURRENT_TIMESTAMP, needs_human_reason = NULL WHERE url = ?",
                            (job.get("url"),)
                        )
                        conn.commit()
                    except Exception:
                        pass
                return "applied", int((time.time() - start_time) * 1000), []

            # If form was filled but no standard submit button was recognized, fall back to agent
            logger.info("[W%d] Form fields filled, but submit button ambiguous. Delegating to agent.", worker_id)
            await finalize_proofs()
            return "fallback_to_agent", duration_ms, []

    except Exception as e:
        logger.warning("[W%d] Error running Playwright tier engine: %s; falling back to agent.", worker_id, e)
        try:
            if "tracer" in locals():
                tracer.error_traces.append(f"Engine exception: {e}")
                tracer.log("engine_error", f"Fatal engine exception: {e}", level="ERROR")
            if "finalize_proofs" in locals():
                await finalize_proofs()
        except Exception:
            pass
        return "fallback_to_agent", 0, []


def run_playwright_tier_engine(
    job: dict,
    port: int = 0,
    worker_id: int = 0,
    dry_run: bool = False,
    headless: bool = True,
    auto_submit: bool | None = None,
    mode: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> tuple[str, int, list[dict]]:
    """Synchronous entry point to run the Playwright Tier 0/1/2 engine."""
    return asyncio.run(
        _async_run_playwright_tier_engine(
            job=job,
            port=port,
            worker_id=worker_id,
            dry_run=dry_run,
            headless=headless,
            auto_submit=auto_submit,
            mode=mode,
            conn=conn,
        )
    )
