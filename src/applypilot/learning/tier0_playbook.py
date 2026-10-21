"""Tier 0: Deterministic ATS Playbook & Selector Replay Engine.

Executes pure Python Playwright form filling using pre-verified CSS/ARIA selectors
from ats_selector_cache and hardcoded ATS baseline playbooks.
Consumes zero AI tokens and executes in milliseconds.
"""

from __future__ import annotations

import logging
import re
import sqlite3
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from applypilot.database import (
    get_connection,
    get_selectors_for_domain,
    record_selector_result,
)
from applypilot.learning.tier2_heuristics import normalize_phone, sanitize_url

logger = logging.getLogger(__name__)

# Baseline deterministic selectors by ATS type
# Maps profile key -> ordered list of fallback selectors
_BASELINE_ATS_SELECTORS: dict[str, dict[str, list[str]]] = {
    "greenhouse": {
        "profile.first_name": [
            "input#first_name",
            "input[name='first_name']",
            "input[autocomplete='given-name']",
        ],
        "profile.last_name": [
            "input#last_name",
            "input[name='last_name']",
            "input[autocomplete='family-name']",
        ],
        "profile.email": [
            "input#email",
            "input[name='email']",
            "input[type='email']",
            "input[autocomplete='email']",
        ],
        "profile.phone": [
            "input#phone",
            "input[name='phone']",
            "input[type='tel']",
            "input[autocomplete='tel']",
        ],
        "profile.linkedin_url": [
            "input#job_application_answers_attributes_0_text_value",
            "input[name*='linkedin' i]",
            "input[aria-label*='linkedin' i]",
            "input[placeholder*='linkedin' i]",
        ],
        "profile.github_url": [
            "input[name*='github' i]",
            "input[aria-label*='github' i]",
            "input[placeholder*='github' i]",
        ],
        "profile.portfolio_url": [
            "input#job_application_answers_attributes_1_text_value",
            "input[name*='website' i]",
            "input[name*='portfolio' i]",
            "input[aria-label*='website' i]",
        ],
        "resume_file": [
            "input#resume[type='file']",
            "input[type='file'][name*='resume' i]",
            "input[type='file'][aria-label*='resume' i]",
            "input[type='file']",
        ],
    },
    "lever": {
        "profile.full_name": [
            "input[name='name']",
            "input#name",
            "input[autocomplete='name']",
        ],
        "profile.email": [
            "input[name='email']",
            "input#email",
            "input[type='email']",
        ],
        "profile.phone": [
            "input[name='phone']",
            "input#phone",
            "input[type='tel']",
        ],
        "profile.current_company": [
            "input[name='org']",
            "input#org",
        ],
        "profile.linkedin_url": [
            "input[name='urls[LinkedIn]']",
            "input[name*='linkedin' i]",
            "input[placeholder*='linkedin' i]",
        ],
        "profile.github_url": [
            "input[name='urls[GitHub]']",
            "input[name*='github' i]",
            "input[placeholder*='github' i]",
        ],
        "profile.portfolio_url": [
            "input[name='urls[Portfolio]']",
            "input[name*='portfolio' i]",
            "input[name*='other' i]",
        ],
        "resume_file": [
            "input#resume-upload-input",
            "input[type='file'][name*='resume' i]",
            "input[type='file']",
        ],
    },
    "workday": {
        "profile.first_name": [
            "input[data-automation-id='legalNameSection_firstName']",
            "input[id*='firstName']",
        ],
        "profile.last_name": [
            "input[data-automation-id='legalNameSection_lastName']",
            "input[id*='lastName']",
        ],
        "profile.email": [
            "input[data-automation-id='email']",
            "input[type='email']",
        ],
        "profile.phone": [
            "input[data-automation-id='phone-number']",
            "input[type='tel']",
        ],
        "profile.address": [
            "input[data-automation-id='addressSection_addressLine1']",
        ],
        "profile.city": [
            "input[data-automation-id='addressSection_city']",
        ],
        "profile.postal_code": [
            "input[data-automation-id='addressSection_postalCode']",
        ],
        "resume_file": [
            "input[data-automation-id='file-upload-input-ref']",
            "input[type='file']",
        ],
    },
    "ashby": {
        "profile.full_name": [
            "input[name='name']",
            "input#name",
        ],
        "profile.email": [
            "input[name='email']",
            "input#email",
            "input[type='email']",
        ],
        "profile.phone": [
            "input[name='phone']",
            "input#phone",
            "input[type='tel']",
        ],
        "profile.linkedin_url": [
            "input[name*='linkedin' i]",
            "input[placeholder*='linkedin' i]",
        ],
        "resume_file": [
            "input[type='file'][name*='resume' i]",
            "input[type='file']",
        ],
    },
}


def detect_form_ats(url: str, html_snippet: str | None = None) -> str:
    """Detect ATS platform from URL or DOM structure."""
    if not url:
        return "custom_domain"

    host = urlparse(url).netloc.lower()

    if "greenhouse.io" in host or "grnh.se" in host:
        return "greenhouse"
    if "lever.co" in host:
        return "lever"
    if "myworkdayjobs.com" in host or "workday.com" in host:
        return "workday"
    if "ashbyhq.com" in host:
        return "ashby"
    if "smartrecruiters.com" in host:
        return "smartrecruiters"
    if "icims.com" in host:
        return "icims"

    # Secondary inspection: check html snippet if available
    if html_snippet:
        snip = html_snippet.lower()
        if "greenhouse" in snip or "gh_jid" in snip:
            return "greenhouse"
        if "lever" in snip:
            return "lever"
        if "myworkdayjobs" in snip or "data-automation-id" in snip:
            return "workday"
        if "ashby" in snip:
            return "ashby"

    return "custom_domain"


def _resolve_profile_value(target_key: str, profile: dict) -> Any:
    """Resolve dot-notation path into profile dictionary."""
    if not profile:
        return None

    # Handle composite full_name
    if target_key == "profile.full_name":
        fn = profile.get("first_name") or ""
        ln = profile.get("last_name") or ""
        full = f"{fn} {ln}".strip()
        return full or profile.get("name")

    # Standard dot notation
    key_path = target_key.replace("profile.", "").split(".")
    curr = profile
    for p in key_path:
        if isinstance(curr, dict):
            curr = curr.get(p)
        else:
            return None
    return curr


def get_tier0_field_mappings(ats_type: str, domain: str,
                             conn: sqlite3.Connection | None = None) -> list[dict]:
    """Retrieve compiled Tier 0 selector mappings (learned + baseline)."""
    mappings: list[dict] = []
    seen_keys: set[str] = set()

    # 1. First add learned verified selectors from SQLite cache
    learned = get_selectors_for_domain(ats_type, domain, conn=conn)
    for sel in learned:
        k = sel.get("target_key")
        if k:
            mappings.append({
                "target_key": k,
                "selector": sel["css_or_aria_selector"],
                "action_type": sel.get("action_type", "fill"),
                "selector_id": sel.get("selector_id"),
                "source": "cache",
            })
            seen_keys.add(k)

    # 2. Add baseline selectors for keys not yet covered
    ats_base = _BASELINE_ATS_SELECTORS.get(ats_type, {})
    for k, selectors in ats_base.items():
        if k not in seen_keys:
            for s in selectors:
                action = "upload" if "file" in k else "fill"
                mappings.append({
                    "target_key": k,
                    "selector": s,
                    "action_type": action,
                    "selector_id": None,
                    "source": "baseline",
                })

    return mappings


async def fill_standard_fields_playwright(page, profile: dict, ats_type: str,
                                         domain: str | None = None,
                                         resume_path: str | None = None,
                                         conn: sqlite3.Connection | None = None) -> dict:
    """Execute Tier 0 deterministic Playwright form fill.

    Fills all recognized fields and uploads the resume file.
    Captures unhandled interactive elements for Tier 1 / HITL resolution.

    Returns:
        {
            "filled": {target_key: value},
            "unresolved": list[dict],
            "duration_ms": int,
        }
    """
    start_time = time.time()
    filled: dict[str, Any] = {}
    if not domain:
        domain = urlparse(page.url).netloc
    mappings = get_tier0_field_mappings(ats_type, domain, conn=conn)

    # Try filling each mapping
    for m in mappings:
        target_key = m["target_key"]
        if target_key in filled:
            continue

        selector = m["selector"]
        action = m["action_type"]
        selector_id = m.get("selector_id")

        try:
            # Check element visibility with short 400ms timeout
            loc = page.locator(selector).first
            if not await loc.is_visible(timeout=400):
                continue

            if action == "upload":
                if resume_path and Path(resume_path).exists():
                    await loc.set_input_files(str(resume_path))
                    filled[target_key] = str(resume_path)
                    if selector_id:
                        record_selector_result(selector_id, success=True, conn=conn)
            else:
                val = _resolve_profile_value(target_key, profile)
                if val:
                    val_str = str(val)
                    if "phone" in target_key:
                        val_str = normalize_phone(val_str)
                    elif "url" in target_key:
                        val_str = sanitize_url(val_str)

                    await loc.fill(val_str)
                    filled[target_key] = val_str
                    if selector_id:
                        record_selector_result(selector_id, success=True, conn=conn)

        except Exception as e:
            logger.debug("Tier 0 failed for %s (%s): %s", target_key, selector, e)
            if selector_id:
                record_selector_result(selector_id, success=False, conn=conn)

    # Scan for remaining interactive form elements on the page that need answers
    unresolved: list[dict] = []
    try:
        # Find unfilled inputs, textareas, and selects
        elements = await page.query_selector_all(
            "input:not([type='hidden']):not([type='submit']):not([type='button']), textarea, select, [role='combobox']"
        )
        for el in elements:
            try:
                if not await el.is_visible():
                    continue

                # Check if already filled
                val = await el.input_value() if await el.evaluate("e => 'value' in e") else ""
                if val and val.strip():
                    continue

                # Extract label & metadata
                tag = await el.evaluate("e => e.tagName.toLowerCase()")
                el_type = await el.get_attribute("type") or tag
                el_id = await el.get_attribute("id") or await el.get_attribute("name") or ""
                required = await el.evaluate("e => e.required || e.getAttribute('aria-required') === 'true'")

                # Extract associated label text
                label = await el.evaluate("""e => {
                    if (e.id) {
                        const lbl = document.querySelector(`label[for="${e.id}"]`);
                        if (lbl) return lbl.innerText;
                    }
                    const parent = e.closest('label');
                    if (parent) return parent.innerText;
                    const container = e.closest('div, fieldset');
                    if (container) {
                        const header = container.querySelector('label, legend, .label');
                        if (header) return header.innerText;
                    }
                    return e.getAttribute('aria-label') || e.getAttribute('placeholder') || '';
                }""")

                # Extract options if select or combobox
                options: list[str] = []
                if tag == "select":
                    options = await el.evaluate("""e => Array.from(e.options).map(o => o.text.trim()).filter(Boolean)""")

                clean_label = " ".join(str(label).split())
                if clean_label or el_id:
                    unresolved.append({
                        "field_id": el_id,
                        "label": clean_label or el_id,
                        "field_type": el_type,
                        "options": options,
                        "required": bool(required),
                    })
            except Exception:
                continue
    except Exception as e:
        logger.debug("Failed scanning unresolved fields: %s", e)

    duration_ms = int((time.time() - start_time) * 1000)
    return {
        "filled": filled,
        "unresolved": unresolved,
        "duration_ms": duration_ms,
    }
