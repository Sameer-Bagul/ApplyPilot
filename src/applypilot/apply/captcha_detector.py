"""CAPTCHA & Security Challenge Detection and HITL Resolver for ApplyPilot.

Provides reliable detection of:
- Cloudflare Turnstile
- Google reCAPTCHA (v2 / Enterprise)
- hCaptcha
- Arkose Labs (FunCaptcha)
- Cloudflare / WAF Bot Interstitial Gates ("Just a moment...", "Verify you are human")
- OTP / 2FA Verification Prompts

Plays an audible chime / alarm to alert the candidate, displays a banner in the
headed browser, and continuously polls until the human has solved the challenge.
Consistently adheres to security guidelines by never attempting to automate or bypass
anti-bot challenges.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from typing import Any

from applypilot.hitl.audio import (
    notify_hitl_needed,
    notify_hitl_resolved,
    play_browser_chime,
    play_system_sound,
)

logger = logging.getLogger(__name__)


async def detect_challenge(page: Any) -> dict[str, Any] | None:
    """Detect if a CAPTCHA or security challenge is currently gating the page.
    
    Uses a robust multi-layered inspection:
    1. Page Title & URL check (Cloudflare / WAF Bot Interstitials)
    2. Playwright page.frames hierarchy inspection (pierces nested & cross-origin iframes)
    3. Visible modal/iframe inspection on the top-level page
    4. In-page DOM evaluation for inline widgets & verification overlays
    """
    try:
        # 1. Check URL or title first
        title = ""
        if hasattr(page, "title") and callable(page.title):
            t_res = page.title()
            title = await t_res if asyncio.iscoroutine(t_res) else str(t_res or "")
        title_lower = title.lower()
        if any(g in title_lower for g in ["just a moment", "attention required", "security check", "cloudflare"]):
            return {
                "type": "bot_gate",
                "name": "Cloudflare / Bot Gate Interstitial",
                "detail": f"Page Title: {title}",
            }

        # 2. Inspect Playwright frame tree (pierces cross-origin / nested iframes)
        frames = getattr(page, "frames", None)
        if isinstance(frames, (list, tuple)):
            for frame in frames:
                f_url = (getattr(frame, "url", "") or "").lower()
                if not any(provider in f_url for provider in ["hcaptcha", "arkoselabs", "funcaptcha", "recaptcha", "datadome", "cloudflare"]):
                    continue

                # Ensure frame is actively displayed to the user (not an invisible background preloader)
                is_frame_vis = True
                if hasattr(frame, "frame_element") and callable(frame.frame_element):
                    try:
                        fe = frame.frame_element()
                        fe_obj = await fe if asyncio.iscoroutine(fe) else fe
                        if fe_obj and hasattr(fe_obj, "is_visible") and callable(fe_obj.is_visible):
                            v_res = fe_obj.is_visible()
                            is_frame_vis = await v_res if asyncio.iscoroutine(v_res) else bool(v_res)
                    except Exception:
                        pass

                if not is_frame_vis:
                    continue

                # (a) hCaptcha challenge subframe (e.g. on Lever, Discord, Epic Games)
                if "hcaptcha.com" in f_url and any(k in f_url for k in ["challenge", "hcaptcha.html"]):
                    try:
                        txt = ""
                        if hasattr(frame, "evaluate") and callable(frame.evaluate):
                            txt = await frame.evaluate("() => document.body ? document.body.innerText.slice(0, 500) : ''")
                        txt_lower = (txt or "").lower()
                        if any(w in txt_lower for w in ["click", "different", "incomplete", "skip", "verify", "try again", "puzzle", "select", "icons"]):
                            return {
                                "type": "hcaptcha",
                                "name": "hCaptcha Security Challenge",
                                "detail": f"Active hCaptcha prompt: {txt[:80].strip()}",
                                "selector": "iframe[src*='hcaptcha']",
                                "frame_url": getattr(frame, "url", ""),
                            }
                    except Exception:
                        pass

                # (b) Arkose Labs / FunCaptcha subframe
                if any(w in f_url for w in ["arkoselabs.com", "funcaptcha.com", "client-api.arkoselabs"]):
                    return {
                        "type": "funcaptcha",
                        "name": "Arkose FunCaptcha",
                        "detail": f"Active Arkose frame: {f_url[:60]}",
                        "selector": "#fc-iframe-wrap, iframe[src*='arkoselabs']",
                        "frame_url": getattr(frame, "url", ""),
                    }

                # (c) Google reCAPTCHA interactive bframe (image challenge)
                if any(w in f_url for w in ["google.com/recaptcha/api2/bframe", "recaptcha/enterprise/bframe"]):
                    return {
                        "type": "recaptcha",
                        "name": "Google reCAPTCHA (Image Challenge)",
                        "detail": "Active reCAPTCHA bframe",
                        "selector": "iframe[title*='recaptcha' i], iframe[src*='bframe']",
                        "frame_url": getattr(frame, "url", ""),
                    }

                # (d) DataDome subframe
                if any(w in f_url for w in ["captcha-delivery.com", "datadome.co"]):
                    return {
                        "type": "datadome",
                        "name": "DataDome CAPTCHA",
                        "detail": "Active DataDome challenge frame",
                        "selector": "iframe[src*='captcha-delivery.com']",
                        "frame_url": getattr(frame, "url", ""),
                    }

        # 3. Inspect visible challenge modal iframes on page
        if hasattr(page, "query_selector_all") and callable(page.query_selector_all):
            try:
                res = page.query_selector_all("iframe")
                if asyncio.iscoroutine(res):
                    iframes = await res
                    if isinstance(iframes, (list, tuple)):
                        for ifr in iframes:
                            try:
                                is_vis = False
                                if hasattr(ifr, "is_visible") and callable(ifr.is_visible):
                                    v_res = ifr.is_visible()
                                    is_vis = await v_res if asyncio.iscoroutine(v_res) else bool(v_res)
                                if is_vis:
                                    box = None
                                    if hasattr(ifr, "bounding_box") and callable(ifr.bounding_box):
                                        b_res = ifr.bounding_box()
                                        box = await b_res if asyncio.iscoroutine(b_res) else b_res
                                    # Active challenge modals take significant viewport area (>120px)
                                    if box and box.get("width", 0) > 120 and box.get("height", 0) > 120:
                                        title_attr = ""
                                        src_attr = ""
                                        if hasattr(ifr, "get_attribute") and callable(ifr.get_attribute):
                                            t_res = ifr.get_attribute("title")
                                            title_attr = (await t_res if asyncio.iscoroutine(t_res) else t_res or "").lower()
                                            s_res = ifr.get_attribute("src")
                                            src_attr = (await s_res if asyncio.iscoroutine(s_res) else s_res or "").lower()

                                        if "hcaptcha" in title_attr or "security challenge" in title_attr or "hcaptcha" in src_attr:
                                            return {
                                                "type": "hcaptcha",
                                                "name": "hCaptcha Security Challenge",
                                                "detail": f"Visible hCaptcha modal (title={title_attr})",
                                                "selector": "iframe[src*='hcaptcha']",
                                            }
                                        if "arkose" in title_attr or "arkoselabs" in src_attr or "funcaptcha" in src_attr:
                                            return {
                                                "type": "funcaptcha",
                                                "name": "Arkose FunCaptcha",
                                                "detail": "Visible Arkose Labs challenge modal",
                                                "selector": "#fc-iframe-wrap",
                                            }
                                        if "recaptcha" in title_attr or "bframe" in src_attr:
                                            return {
                                                "type": "recaptcha",
                                                "name": "Google reCAPTCHA (Image Challenge)",
                                                "detail": "Visible reCAPTCHA challenge modal",
                                                "selector": "iframe[title*='recaptcha' i]",
                                            }
                                        if "challenges.cloudflare.com" in src_attr:
                                            return {
                                                "type": "turnstile",
                                                "name": "Cloudflare Turnstile",
                                                "detail": "Visible Turnstile widget",
                                                "selector": "iframe[src*='challenges.cloudflare.com']",
                                            }
                                        if "captcha-delivery" in src_attr or "datadome" in src_attr or "datadome" in title_attr:
                                            return {
                                                "type": "datadome",
                                                "name": "DataDome CAPTCHA",
                                                "detail": "Visible DataDome modal",
                                                "selector": "iframe[src*='captcha-delivery.com']",
                                            }
                            except Exception:
                                continue
            except Exception:
                pass

        # 4. Check DOM via in-page evaluate
        check_script = """
        () => {
            const isVisible = (el) => {
                if (!el) return false;
                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
                const rect = el.getBoundingClientRect();
                return rect.width > 20 && rect.height > 20;
            };

            // 1. Cloudflare Turnstile (active interactive widget)
            const cfIframe = document.querySelector('iframe[src*="challenges.cloudflare.com"]');
            const cfElem = document.querySelector('.cf-turnstile, [data-turnstile-sitekey]');
            const cfInput = document.querySelector('input[name="cf-turnstile-response"]');
            if ((cfIframe && isVisible(cfIframe)) || (cfElem && isVisible(cfElem))) {
                if (!cfInput || !cfInput.value || cfInput.value.length < 10) {
                    return { type: 'turnstile', name: 'Cloudflare Turnstile', selector: 'iframe[src*="challenges.cloudflare.com"]' };
                }
            }

            // 2. Google reCAPTCHA
            // (a) Active interactive image challenge popup (bframe)
            const rcChallengeIframe = document.querySelector('iframe[title*="recaptcha challenge" i], iframe[src*="google.com/recaptcha/api2/bframe"]');
            if (rcChallengeIframe && isVisible(rcChallengeIframe)) {
                return { type: 'recaptcha', name: 'Google reCAPTCHA (Image Challenge)', selector: 'iframe[title*="recaptcha challenge" i]' };
            }

            // (b) Active visible reCAPTCHA checkbox (not invisible badge)
            const rcAnchorIframe = document.querySelector('iframe[src*="google.com/recaptcha/api2/anchor"]');
            const rcElem = document.querySelector('.g-recaptcha:not([data-size="invisible"]), #recaptcha:not([data-size="invisible"])');
            const rcText = document.querySelector('textarea[name="g-recaptcha-response"]');
            if (((rcAnchorIframe && isVisible(rcAnchorIframe)) || (rcElem && isVisible(rcElem)))) {
                if (!rcText || !rcText.value || rcText.value.length < 10) {
                    return { type: 'recaptcha', name: 'Google reCAPTCHA', selector: 'iframe[src*="google.com/recaptcha"]' };
                }
            }

            // 3. hCaptcha
            const hcChallengeIframe = document.querySelector('iframe[title*="hCaptcha" i], iframe[title*="security challenge" i], iframe[src*="hcaptcha.com"]');
            if (hcChallengeIframe && isVisible(hcChallengeIframe)) {
                const rect = hcChallengeIframe.getBoundingClientRect();
                if (rect.width > 120 && rect.height > 120) {
                    return { type: 'hcaptcha', name: 'hCaptcha Security Challenge', selector: 'iframe[src*="hcaptcha.com"]' };
                }
            }
            const hcElem = document.querySelector('.h-captcha:not([data-size="invisible"])');
            const hcText = document.querySelector('textarea[name="h-captcha-response"], input#hcaptchaResponseInput');
            if (hcElem && isVisible(hcElem)) {
                if (!hcText || !hcText.value || hcText.value.length < 10) {
                    return { type: 'hcaptcha', name: 'hCaptcha', selector: '.h-captcha' };
                }
            }

            // 4. Arkose Labs / FunCaptcha
            const fcIframe = document.querySelector('iframe[src*="arkoselabs"], iframe[src*="funcaptcha"], iframe#fc-iframe-wrap');
            const fcElem = document.querySelector('#FunCaptcha, .funcaptcha, #fc-iframe-wrap, [id*="arkose" i]');
            if ((fcIframe && isVisible(fcIframe)) || (fcElem && isVisible(fcElem))) {
                return { type: 'funcaptcha', name: 'Arkose FunCaptcha', selector: '#FunCaptcha' };
            }

            // 5. DataDome CAPTCHA (e.g. on SmartRecruiters)
            const ddIframe = document.querySelector('iframe[src*="captcha-delivery.com"], iframe[title*="DataDome" i], iframe[src*="datadome.co"]');
            if (ddIframe && isVisible(ddIframe)) {
                return { type: 'datadome', name: 'DataDome CAPTCHA', selector: 'iframe[src*="captcha-delivery.com"]' };
            }

            // 6. Text-based Bot Verification Gate & Visual Puzzle Prompts
            const bodyText = (document.body ? document.body.innerText : '').slice(0, 3000).toLowerCase();
            if (
                bodyText.includes('icons that are different') ||
                bodyText.includes('click on the two icons') ||
                bodyText.includes('click the incomplete') ||
                bodyText.includes('please solve this puzzle')
            ) {
                return { type: 'hcaptcha', name: 'hCaptcha Visual Challenge', selector: 'body' };
            }
            if (
                bodyText.includes('verify you are human') ||
                bodyText.includes('verify you are a human') ||
                bodyText.includes('confirm you are human') ||
                bodyText.includes('please complete the security check') ||
                bodyText.includes('human verification')
            ) {
                return { type: 'bot_gate', name: 'Human Verification Gate', selector: 'body' };
            }

            // 7. OTP / Verification Code modal
            if (
                bodyText.includes('enter the verification code') ||
                bodyText.includes('enter the 6-digit code') ||
                bodyText.includes('check your email for a verification code')
            ) {
                return { type: 'otp_verification', name: 'Email/SMS Verification Code', selector: 'body' };
            }

            return null;
        }
        """
        if hasattr(page, "evaluate") and callable(page.evaluate):
            e_res = page.evaluate(check_script)
            result = await e_res if asyncio.iscoroutine(e_res) else e_res
            if isinstance(result, dict):
                return result
        return None
    except Exception as e:
        logger.debug("Error during challenge detection: %s", e)
        return None


async def is_challenge_solved(page: Any, challenge: dict[str, Any]) -> bool:
    """Check whether the detected challenge has been successfully completed by the user."""
    try:
        ctype = challenge.get("type")

        # Check if URL navigated away to confirmation
        cur_url = getattr(page, "url", "") or ""
        if any(x in cur_url.lower() for x in ["/thanks", "/thank-you", "/confirmation", "/applied", "/submitted", "/success"]):
            return True

        check_script = """
        (ctype) => {
            if (ctype === 'turnstile') {
                const input = document.querySelector('input[name="cf-turnstile-response"]');
                if (input && input.value && input.value.length > 10) return true;
                const iframe = document.querySelector('iframe[src*="challenges.cloudflare.com"]');
                if (!iframe) return true;
                return false;
            }

            if (ctype === 'recaptcha') {
                const text = document.querySelector('textarea[name="g-recaptcha-response"]');
                if (text && text.value && text.value.length > 10) return true;
                const bframe = document.querySelector('iframe[src*="recaptcha/api2/bframe"], iframe[title*="recaptcha challenge" i]');
                if (!bframe) return true;
                const style = window.getComputedStyle(bframe);
                if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return true;
                return false;
            }

            if (ctype === 'hcaptcha') {
                const text = document.querySelector('textarea[name="h-captcha-response"], input#hcaptchaResponseInput, input[name="h-captcha-response"]');
                if (text && text.value && text.value.length > 10) return true;
                
                // Check if the modal overlay has closed
                const iframes = Array.from(document.querySelectorAll('iframe'));
                const activeModal = iframes.find(f => {
                    const style = window.getComputedStyle(f);
                    const isVis = style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
                    const rect = f.getBoundingClientRect();
                    const title = (f.title || '').toLowerCase();
                    const src = (f.src || '').toLowerCase();
                    return isVis && rect.width > 120 && rect.height > 120 && (title.includes('security challenge') || src.includes('hcaptcha'));
                });
                if (!activeModal) return true;
                return false;
            }

            if (ctype === 'funcaptcha') {
                const fc = document.querySelector('#fc-iframe-wrap, [id*="arkose" i]');
                if (!fc) return true;
                const style = window.getComputedStyle(fc);
                if (style.display === 'none' || style.visibility === 'hidden') return true;
                return false;
            }

            if (ctype === 'datadome') {
                const ddIframe = document.querySelector('iframe[src*="captcha-delivery.com"], iframe[title*="DataDome" i], iframe[src*="datadome.co"]');
                return !ddIframe;
            }

            if (ctype === 'bot_gate') {
                const title = (document.title || '').toLowerCase();
                if (title.includes('just a moment') || title.includes('attention required')) return false;
                const bodyText = (document.body ? document.body.innerText : '').slice(0, 3000).toLowerCase();
                if (bodyText.includes('verify you are human') || bodyText.includes('confirm you are human')) {
                    return false;
                }
                return true;
            }

            if (ctype === 'otp_verification') {
                const bodyText = (document.body ? document.body.innerText : '').slice(0, 3000).toLowerCase();
                if (bodyText.includes('enter the verification code') || bodyText.includes('enter the 6-digit code')) {
                    return false;
                }
                return true;
            }

            return true;
        }
        """
        if hasattr(page, "evaluate") and callable(page.evaluate):
            e_res = page.evaluate(check_script, ctype)
            solved = await e_res if asyncio.iscoroutine(e_res) else bool(e_res)
            return bool(solved)
        return False
    except Exception as e:
        logger.debug("Error checking challenge solved status: %s", e)
        # If page navigated away or closed, treat as potential progression
        return False


async def inject_hitl_banner(page: Any, message: str, bg_color: str = "#d97706") -> None:
    """Inject a prominent, non-obtrusive floating banner at the top of the browser page."""
    try:
        banner_script = """
        ({msg, bg}) => {
            let el = document.getElementById('applypilot-hitl-banner');
            if (!el) {
                el = document.createElement('div');
                el.id = 'applypilot-hitl-banner';
                document.body.prepend(el);
            }
            el.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                background: ${bg};
                color: #ffffff;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-size: 14px;
                font-weight: 600;
                padding: 12px 20px;
                z-index: 2147483647;
                display: flex;
                align-items: center;
                justify-content: space-between;
                box-shadow: 0 4px 16px rgba(0,0,0,0.3);
                letter-spacing: 0.2px;
            `;
            el.innerHTML = `
                <div style="display:flex;align-items:center;gap:12px;">
                    <span style="font-size:18px;">🔔</span>
                    <span><strong>ApplyPilot Autonomous Engine:</strong> ${msg}</span>
                </div>
                <div style="font-size:12px;opacity:0.9;padding:4px 10px;background:rgba(255,255,255,0.2);border-radius:6px;">
                    Auto-detecting when completed...
                </div>
            `;
        }
        """
        await page.evaluate(banner_script, {"msg": message, "bg": bg_color})
    except Exception as e:
        logger.debug("Failed injecting banner: %s", e)


async def remove_hitl_banner(page: Any) -> None:
    """Remove the injected notification banner from the browser page."""
    try:
        await page.evaluate("""() => {
            const el = document.getElementById('applypilot-hitl-banner');
            if (el) el.remove();
        }""")
    except Exception:
        pass


async def wait_for_human_challenge_resolution(
    page: Any,
    challenge: dict[str, Any],
    timeout_sec: int = 300,
    check_interval: float = 1.5,
) -> bool:
    """Wait for human user to solve the CAPTCHA or verification challenge.

    1. Alerts user with system audio (paplay/canberra-gtk-play) + browser chime + terminal bell.
    2. Shows an interactive banner on the page.
    3. Prints clear guidance in the terminal.
    4. Chimes gently every 20 seconds while waiting.
    5. Detects resolution automatically, rings success sound, and returns True.
    """
    ch_name = challenge.get("name", "CAPTCHA / Security Challenge")
    logger.info("Human intervention needed: %s", ch_name)

    # 1. Trigger Multi-Tier Sound Alert
    notify_hitl_needed(page, reason=ch_name)

    # 2. Inject Visual Banner in Headed Browser
    banner_msg = f"{ch_name} detected! Please complete it in this window. ApplyPilot will auto-resume."
    await inject_hitl_banner(page, banner_msg, bg_color="#b45309")

    # 3. Print High-Visibility Banner in Console
    print("\n" + "═" * 76)
    print(f"🔔 [HITL ACTION REQUIRED] {ch_name.upper()} DETECTED!")
    print("═" * 76)
    print(f"  Target URL: {page.url}")
    print("  👉 The headed browser window is open on your screen.")
    print("  👉 Please complete the challenge or CAPTCHA directly in the browser.")
    print("  ApplyPilot is listening and will automatically detect when solved!")
    print("═" * 76 + "\n", flush=True)

    start_time = time.time()
    last_chime_time = start_time

    while time.time() - start_time < timeout_sec:
        # Check if solved
        solved = await is_challenge_solved(page, challenge)
        if solved:
            logger.info("Challenge %s resolved successfully by human!", ch_name)
            # Update banner to green success
            await inject_hitl_banner(page, "✓ Challenge verified! Continuing application...", bg_color="#15803d")
            notify_hitl_resolved(page)
            print("\n✓ [HITL RESOLVED] Verification confirmed! Resuming automated application...\n", flush=True)
            await page.wait_for_timeout(1200)
            await remove_hitl_banner(page)
            return True

        # Gentle reminder chime every 20 seconds
        if time.time() - last_chime_time >= 20.0:
            play_system_sound("alert")
            try:
                await play_browser_chime(page, "alert")
            except Exception:
                pass
            last_chime_time = time.time()

        await asyncio.sleep(check_interval)

    # Timed out
    logger.warning("HITL challenge resolution timed out after %d seconds.", timeout_sec)
    await remove_hitl_banner(page)
    return False
