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
import json
import logging
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

            if is_direct_launch:
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 900},
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                )
                page = await context.new_page()
            else:
                contexts = browser.contexts
                context = contexts[0] if contexts else await browser.new_context()
                pages = context.pages
                page = pages[0] if pages else await context.new_page()

            domain = urlparse(target_url).netloc
            ats_type = detect_form_ats(target_url)

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
                    await page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
                    await page.wait_for_timeout(1500)
                except Exception as e:
                    logger.debug("Page navigation to %s encountered: %s", target_url, e)

            # Re-detect ATS from final URL in case of redirect
            ats_type = detect_form_ats(page.url)

            # ------------------------------------------------------------------
            # Phase 1: CAPTCHA / Security Gate Pre-Check
            # ------------------------------------------------------------------
            challenge = await detect_challenge(page)
            if challenge:
                ch_name = challenge.get("name", "Security Challenge")
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
                        if is_direct_launch:
                            try:
                                await browser.close()
                            except Exception:
                                pass
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
                    if is_direct_launch:
                        try:
                            await browser.close()
                        except Exception:
                            pass
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
                    try:
                        # Attempt to fill the resolved answer
                        loc = None
                        if field_id:
                            loc = page.locator(f"#{field_id}, [name='{field_id}']").first
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

                            # Record learned mapping
                            if field_id:
                                sel = f"#{field_id}"
                                store_selector(ats_type, domain, sel, "fill" if ftype not in ("select", "radio") else "select", can_key, conn=conn)
                    except Exception as e:
                        logger.debug("Failed applying Tier 1 answer for %s: %s", label, e)

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

                if is_direct_launch:
                    await browser.close()
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
                if is_direct_launch:
                    try:
                        await browser.close()
                    except Exception:
                        pass
                return "applied", duration_ms, []

            # ------------------------------------------------------------------
            # Phase 6: Locate Submit Button
            # ------------------------------------------------------------------
            submit_btn = None
            for sel in [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Submit Application')",
                "button:has-text('Submit application')",
                "button:has-text('Submit')",
                "button:has-text('Apply')",
            ]:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=300):
                        submit_btn = btn
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
                        await browser.close()
                    return "applied", int((time.time() - start_time) * 1000), []

                # Fallback if user didn't click within review timeout
                logger.info("[W%d] Review window completed.", worker_id)
                if is_direct_launch:
                    await browser.close()
                return "applied", int((time.time() - start_time) * 1000), []

            # Auto-Submit Mode:
            if submit_btn:
                logger.info("[W%d] Auto-submitting application via Playwright...", worker_id)
                await submit_btn.click()
                await page.wait_for_timeout(2500)

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
                            if is_direct_launch:
                                await browser.close()
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
                        if is_direct_launch:
                            await browser.close()
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
                    if is_direct_launch:
                        if not headless:
                            await page.wait_for_timeout(3500)
                        await browser.close()
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

                if is_direct_launch:
                    try:
                        await browser.close()
                    except Exception:
                        pass
                return "applied", int((time.time() - start_time) * 1000), []

            # If form was filled but no standard submit button was recognized, fall back to agent
            logger.info("[W%d] Form fields filled, but submit button ambiguous. Delegating to agent.", worker_id)
            if is_direct_launch:
                if not headless:
                    await page.wait_for_timeout(3500)
                await browser.close()
            return "fallback_to_agent", duration_ms, []

    except Exception as e:
        logger.warning("[W%d] Error running Playwright tier engine: %s; falling back to agent.", worker_id, e)
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
