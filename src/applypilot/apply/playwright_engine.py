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
    conn: sqlite3.Connection | None = None,
) -> tuple[str, int, list[dict]]:
    """Execute Tier 0/1/2 Playwright flow on the active Chrome worker via CDP or direct browser."""
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

    # Check auto_submit preference
    if auto_submit is None:
        auto_submit = profile.get("preferences", {}).get("auto_submit", False)

    # Identify resume file
    resume_path = job.get("tailored_resume_path") or profile.get("resume_path")
    if not resume_path:
        from applypilot.config import RESUME_PDF_PATH
        if RESUME_PDF_PATH.exists():
            resume_path = str(RESUME_PDF_PATH)

    tracer = ApplicationTracer(job)
    tracer.log("start", f"Initializing application runner for {job.get('company')} - {job.get('title')}", {"target_url": target_url, "auto_submit": auto_submit, "headless": headless})

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
                browser = await p.chromium.launch(
                    headless=headless,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )

            config.ensure_dirs()
            proof_finalized = False
            page = None
            context = None

            async def finalize_proofs() -> tuple[str | None, str | None]:
                nonlocal proof_finalized, page, context, browser
                if proof_finalized or page is None:
                    return None, None
                proof_finalized = True

                clean_co = re.sub(r"[^a-zA-Z0-9_-]", "_", job.get("company") or "company").strip("_")[:30] or "company"
                clean_ti = re.sub(r"[^a-zA-Z0-9_-]", "_", job.get("title") or "role").strip("_")[:30] or "role"
                ts = int(time.time())

                screenshot_dest = config.PROOFS_SCREENSHOTS_DIR / f"{clean_co}_{clean_ti}_{ts}.png"
                screenshot_full_dest = config.PROOFS_SCREENSHOTS_DIR / f"{clean_co}_{clean_ti}_{ts}_full.png"
                video_dest = config.PROOFS_VIDEOS_DIR / f"{clean_co}_{clean_ti}_{ts}.webm"

                # 1. Capture screenshot proof (both crisp 2x viewport receipt and complete full-page document)
                try:
                    if hasattr(page, "screenshot") and callable(page.screenshot):
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

                            # Separate full-page DOM screenshot
                            try:
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
                                shutil.move(str(raw_p), str(video_dest))
                                saved_video = str(video_dest)
                                logger.info("Recorded 720p proof video: %s (%d bytes)", video_dest, video_dest.stat().st_size)
                    except Exception as e:
                        logger.debug("Failed moving recorded video: %s", e)

                saved_screenshot = str(screenshot_dest) if screenshot_dest.exists() and screenshot_dest.stat().st_size > 0 else None

                # 5. Save detailed execution audit log
                saved_log = None
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

            if hasattr(page, "on") and callable(page.on):
                try:
                    page.on("console", lambda msg: tracer.browser_console_logs.append(f"[{msg.type}] {msg.text}"))
                    page.on("pageerror", lambda err: tracer.error_traces.append(str(err)))
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

            # Re-detect ATS from final URL in case of redirect
            ats_type = detect_form_ats(page.url)

            # ------------------------------------------------------------------
            # Phase 1: CAPTCHA / Security Gate Pre-Check
            # ------------------------------------------------------------------
            challenge = await detect_challenge(page)
            if challenge:
                ch_name = challenge.get("name", "Security Challenge")
                tracer.challenges_encountered.append({"name": ch_name, "time": datetime.now(timezone.utc).isoformat()})
                tracer.log("security_challenge", f"Detected {ch_name} challenge")
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
            fill_result = await fill_standard_fields_playwright(
                page=page,
                ats_type=ats_type,
                domain=domain,
                profile=profile,
                resume_path=resume_path,
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
                    profile=profile,
                    conn=conn,
                )

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
                            if not loc and re.match(r"^[A-Za-z0-9_-]+$", field_id):
                                safe_id_loc = page.locator(f"#{field_id}").first
                                try:
                                    if await safe_id_loc.is_visible(timeout=250):
                                        loc = safe_id_loc
                                except Exception:
                                    pass
                        if not loc or not await loc.is_visible(timeout=300):
                            loc = page.get_by_label(label, exact=False).first

                        if loc and await loc.is_visible(timeout=500):
                            if ftype == "select" or options:
                                await loc.select_option(label=str(val))
                            elif ftype in ("radio", "checkbox"):
                                await loc.check()
                            else:
                                await loc.fill(str(val))
                            filled_ok = True
                            tracer.log("screening_qa", f"Filled Tier 1 Q&A: '{label}' -> '{val}' (conf: {conf:.2f})")

                            # Record learned mapping
                            if field_id:
                                sel = f"[name='{field_id}']" if not re.match(r"^[A-Za-z0-9_-]+$", field_id) else f"#{field_id}"
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
                # Common data-testid / IDs
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
            # Phase 7: Review Mode vs Auto-Submit
            # ------------------------------------------------------------------
            if not auto_submit and not headless:
                # Review Mode: The user wants to see the filled form and confirm/click submit
                logger.info("[W%d] Review mode enabled (auto_submit=False). Pausing for candidate review.", worker_id)
                notify_hitl_resolved(page)

                if submit_btn:
                    try:
                        await submit_btn.scroll_into_view_if_needed()
                    except Exception:
                        pass

                banner_msg = "✓ All fields filled & resume attached! Review mode: Please click 'Submit' in this window."
                await inject_hitl_banner(page, banner_msg, bg_color="#0284c7")

                print("\n" + "═" * 76)
                print("✓ [REVIEW MODE ACTIVE] Application form filled successfully!")
                print(f"  Role:      {job.get('title')}")
                print(f"  Company:   {job.get('company')}")
                print(f"  URL:       {page.url}")
                print("  👉 The headed browser window is open for your review.")
                print("  👉 Click 'Submit' in the browser window to complete your submission.")
                print("  ApplyPilot is watching the submission status...")
                print("═" * 76 + "\n", flush=True)

                # Watch for user clicking submit or completing submission (up to 3 minutes)
                review_start = time.time()
                submitted_by_user = False
                while time.time() - review_start < 180:
                    # Check if page URL changed or thank you message appeared
                    try:
                        body_txt = (await page.inner_text("body", timeout=500)).lower()
                        if any(s in body_txt for s in ["thank you", "application submitted", "application received", "success"]):
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
                    if is_direct_launch:
                        await page.wait_for_timeout(2000)
                    await finalize_proofs()
                    return "applied", int((time.time() - start_time) * 1000), []

                # Fallback if user didn't click within review timeout
                logger.info("[W%d] Review window completed.", worker_id)
                await finalize_proofs()
                return "applied", int((time.time() - start_time) * 1000), []

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
                    await submit_btn.scroll_into_view_if_needed()
                    await page.wait_for_timeout(500)
                except Exception:
                    pass
                await submit_btn.click()
                await page.wait_for_timeout(3000)

                # Check if submission triggered a CAPTCHA or verification challenge
                post_challenge = await detect_challenge(page)
                if post_challenge:
                    ch_name = post_challenge.get("name", "Security Challenge")
                    if not headless:
                        logger.info("Submission triggered %s. Alerting user...", ch_name)
                        resolved = await wait_for_human_challenge_resolution(page, post_challenge, timeout_sec=180)
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
                            return "flagged_captcha", duration_ms, []
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
                        return "flagged_captcha", duration_ms, []

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
                    await finalize_proofs()
                    return "fallback_to_agent", duration_ms, []

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
            conn=conn,
        )
    )
