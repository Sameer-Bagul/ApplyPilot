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
    """Detect if a CAPTCHA or security challenge is currently gating the page."""
    try:
        # Check URL or title first
        title = await page.title()
        title_lower = (title or "").lower()
        if any(g in title_lower for g in ["just a moment", "attention required", "security check", "cloudflare"]):
            return {
                "type": "bot_gate",
                "name": "Cloudflare / Bot Gate Interstitial",
                "detail": f"Page Title: {title}",
            }

        # Check DOM via in-page evaluate
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
            const hcChallengeIframe = document.querySelector('iframe[title*="hCaptcha challenge" i], iframe[src*="hcaptcha.com"][src*="frame=challenge"]');
            if (hcChallengeIframe && isVisible(hcChallengeIframe)) {
                return { type: 'hcaptcha', name: 'hCaptcha Challenge', selector: 'iframe[src*="hcaptcha.com"]' };
            }
            const hcIframe = document.querySelector('iframe[src*="hcaptcha.com"]');
            const hcElem = document.querySelector('.h-captcha:not([data-size="invisible"])');
            const hcText = document.querySelector('textarea[name="h-captcha-response"]');
            if ((hcIframe && isVisible(hcIframe)) || (hcElem && isVisible(hcElem))) {
                if (!hcText || !hcText.value || hcText.value.length < 10) {
                    return { type: 'hcaptcha', name: 'hCaptcha', selector: '.h-captcha' };
                }
            }

            // 4. Arkose Labs / FunCaptcha
            const fcIframe = document.querySelector('iframe[src*="arkoselabs"], iframe[src*="funcaptcha"]');
            const fcElem = document.querySelector('#FunCaptcha, .funcaptcha');
            if ((fcIframe && isVisible(fcIframe)) || (fcElem && isVisible(fcElem))) {
                return { type: 'funcaptcha', name: 'Arkose FunCaptcha', selector: '#FunCaptcha' };
            }

            // 5. Text-based Bot Verification Gate
            const bodyText = (document.body ? document.body.innerText : '').slice(0, 3000).toLowerCase();
            if (
                bodyText.includes('verify you are human') ||
                bodyText.includes('verify you are a human') ||
                bodyText.includes('confirm you are human') ||
                bodyText.includes('please complete the security check') ||
                bodyText.includes('human verification')
            ) {
                return { type: 'bot_gate', name: 'Human Verification Gate', selector: 'body' };
            }

            // 6. OTP / Verification Code modal
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
        result = await page.evaluate(check_script)
        return result
    except Exception as e:
        logger.debug("Error during challenge detection: %s", e)
        return None


async def is_challenge_solved(page: Any, challenge: dict[str, Any]) -> bool:
    """Check whether the detected challenge has been successfully completed by the user."""
    try:
        ctype = challenge.get("type")

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
                return false;
            }

            if (ctype === 'hcaptcha') {
                const text = document.querySelector('textarea[name="h-captcha-response"]');
                if (text && text.value && text.value.length > 10) return true;
                return false;
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
        solved = await page.evaluate(check_script, ctype)
        return bool(solved)
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
