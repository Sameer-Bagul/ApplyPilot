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
            "input[name='_systemfield_name']",
            "input#_systemfield_name",
            "input[name='name']",
            "input#name",
            "input[autocomplete='name']",
            "input[placeholder*='name' i]",
        ],
        "profile.email": [
            "input[name='_systemfield_email']",
            "input#_systemfield_email",
            "input[name='email']",
            "input#email",
            "input[type='email']",
        ],
        "profile.phone": [
            "input[name='_systemfield_phone']",
            "input#_systemfield_phone",
            "input[name='phone']",
            "input#phone",
            "input[type='tel']",
        ],
        "profile.linkedin_url": [
            "input[name*='linkedin' i]",
            "input[placeholder*='linkedin' i]",
        ],
        "profile.github_url": [
            "input[name*='github' i]",
            "input[placeholder*='github' i]",
        ],
        "profile.portfolio_url": [
            "input[name*='website' i]",
            "input[name*='portfolio' i]",
        ],
        "resume_file": [
            "input[type='file'][name*='resume' i]",
            "input[type='file']",
        ],
    },
    "smartrecruiters": {
        "profile.first_name": [
            "input[name='firstName']",
            "input#firstName",
        ],
        "profile.last_name": [
            "input[name='lastName']",
            "input#lastName",
        ],
        "profile.email": [
            "input[name='email']",
            "input#email",
            "input[type='email']",
        ],
        "profile.phone": [
            "input[name='phoneNumber']",
            "input#phoneNumber",
            "input[type='tel']",
        ],
        "profile.city": [
            "input[name='city']",
            "input#city",
        ],
        "resume_file": [
            "input[type='file']",
        ],
    },
    "workable": {
        "profile.first_name": [
            "input[data-ui='firstname']",
            "input#firstname",
            "input[name='firstname']",
        ],
        "profile.last_name": [
            "input[data-ui='lastname']",
            "input#lastname",
            "input[name='lastname']",
        ],
        "profile.email": [
            "input[data-ui='email']",
            "input#email",
            "input[name='email']",
            "input[type='email']",
        ],
        "profile.phone": [
            "input#input_phone",
            "input[data-ui='phone']",
            "input[name='phone']",
            "input[type='tel']",
        ],
        "profile.address": [
            "input[data-ui='address']",
            "input#address",
            "input[name='address']",
        ],
        "profile.city": [
            "input#city",
            "input[name='city']",
        ],
        "profile.postal_code": [
            "input#postcode",
            "input[name='postcode']",
        ],
        "profile.headline": [
            "input[data-ui='headline']",
            "input#headline",
            "input[name='headline']",
        ],
        "profile.summary": [
            "textarea[data-ui='summary']",
            "textarea#summary",
            "textarea[name='summary']",
        ],
        "resume_file": [
            "input[data-ui='resume'][type='file']",
            "input[type='file'][name*='resume' i]",
            "input[type='file']",
        ],
    },
    "custom_domain": {
        "profile.first_name": [
            "input[name*='first_name' i]",
            "input[name*='firstName' i]",
            "input[id*='first_name' i]",
            "input[id*='firstName' i]",
            "input[autocomplete='given-name']",
        ],
        "profile.last_name": [
            "input[name*='last_name' i]",
            "input[name*='lastName' i]",
            "input[id*='last_name' i]",
            "input[id*='lastName' i]",
            "input[autocomplete='family-name']",
        ],
        "profile.full_name": [
            "input[name='name' i]",
            "input[name*='full_name' i]",
            "input[name*='fullName' i]",
            "input[id*='full_name' i]",
            "input[autocomplete='name']",
        ],
        "profile.email": [
            "input[type='email']",
            "input[name*='email' i]",
            "input[id*='email' i]",
            "input[autocomplete='email']",
        ],
        "profile.phone": [
            "input[type='tel']",
            "input[name*='phone' i]",
            "input[id*='phone' i]",
            "input[autocomplete='tel']",
        ],
        "profile.linkedin_url": [
            "input[name*='linkedin' i]",
            "input[placeholder*='linkedin' i]",
            "input[aria-label*='linkedin' i]",
        ],
        "profile.github_url": [
            "input[name*='github' i]",
            "input[placeholder*='github' i]",
            "input[aria-label*='github' i]",
        ],
        "profile.portfolio_url": [
            "input[name*='portfolio' i]",
            "input[name*='website' i]",
            "input[placeholder*='portfolio' i]",
            "input[placeholder*='website' i]",
        ],
        "resume_file": [
            "input[type='file'][name*='resume' i]",
            "input[type='file'][name*='cv' i]",
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
    if "workable.com" in host:
        return "workable"
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
    """Resolve dot-notation path into profile dictionary supporting nested structures & aliases."""
    if not profile:
        return None

    # Handle full_name
    if target_key in ("profile.full_name", "profile.name"):
        fn = profile.get("first_name") or ""
        ln = profile.get("last_name") or ""
        full = f"{fn} {ln}".strip()
        return full or profile.get("name")

    # Handle common aliases and nested paths
    aliases = {
        "profile.linkedin_url": [
            ("urls", "linkedin"),
            "linkedin_url",
            "linkedin",
        ],
        "profile.github_url": [
            ("urls", "github"),
            "github_url",
            "github",
        ],
        "profile.portfolio_url": [
            ("urls", "portfolio"),
            "portfolio_url",
            "portfolio",
            ("urls", "website"),
        ],
        "profile.city": [
            ("location", "city"),
            "city",
        ],
        "profile.state": [
            ("location", "state"),
            "state",
        ],
        "profile.country": [
            ("location", "country"),
            "country",
        ],
        "profile.postal_code": [
            ("location", "postal_code"),
            "postal_code",
            "zip_code",
        ],
        "profile.headline": [
            "current_title",
            "headline",
            "title",
            "professional_title",
        ],
        "profile.address": [
            ("location", "address"),
            ("location", "city"),
        ],
        "profile.current_company": [
            "current_company",
            ("experiences", 0, "company"),
        ],
        "profile.current_title": [
            "current_title",
            ("experiences", 0, "title"),
        ],
        "profile.years_of_experience": [
            "years_of_experience",
        ],
        "profile.notice_period": [
            "notice_period",
        ],
        "profile.salary_expectation": [
            ("compensation", "target_salary"),
            ("compensation", "target_salary_numeric"),
        ],
        "profile.work_authorization": [
            ("work_authorization", "authorized_in_target"),
        ],
        "profile.requires_sponsorship": [
            ("work_authorization", "requires_sponsorship"),
        ],
    }

    if target_key in aliases:
        for candidate in aliases[target_key]:
            if isinstance(candidate, (tuple, list)):
                val = profile
                for part in candidate:
                    if isinstance(val, dict) and part in val:
                        val = val[part]
                    elif isinstance(val, list) and isinstance(part, int) and len(val) > part:
                        val = val[part]
                    else:
                        val = None
                        break
                if val is not None and str(val).strip():
                    return val
            elif candidate in profile and profile[candidate]:
                return profile[candidate]

    # Standard dot notation fallback
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
                action = "upload" if ("resume" in k or k.endswith("_file")) else "fill"
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

    # Scan for remaining interactive form elements on the page that need answers (single fast evaluate)
    unresolved: list[dict] = []
    try:
        scan_script = """
        () => {
            const isVisible = (el) => {
                if (!el) return false;
                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
                const rect = el.getBoundingClientRect();
                return rect.width > 0 && rect.height > 0;
            };

            const list = [];
            const elements = document.querySelectorAll(
                "input:not([type='hidden']):not([type='submit']):not([type='button']), textarea, select, [role='combobox']"
            );

            for (const el of elements) {
                if (!isVisible(el)) continue;
                const val = ('value' in el) ? el.value : '';
                if (val && val.trim()) continue;

                const tag = el.tagName.toLowerCase();
                const elType = el.getAttribute('type') || tag;
                const elId = el.getAttribute('id') || el.getAttribute('name') || '';
                const required = el.required || el.getAttribute('aria-required') === 'true';

                let label = '';
                if (el.id) {
                    const lbl = document.querySelector(`label[for="${el.id}"], #${el.id}_label, #${el.id}-label`);
                    if (lbl) label = lbl.innerText;
                }
                if (!label) {
                    const parent = el.closest('label');
                    if (parent) label = parent.innerText;
                }
                if (!label) {
                    const qCard = el.closest('.application-question, .card-field, [data-qa*="custom"], .form-group, .field, fieldset, li, .section-wrapper');
                    if (qCard) {
                        const header = qCard.querySelector('.application-label, .card-field-name, .text, label, legend, .label, .prompt, h3, h4');
                        if (header) label = header.innerText;
                    }
                }
                if (!label) {
                    const container = el.closest('div, fieldset');
                    if (container) {
                        const header = container.querySelector('label, legend, .label, .application-label');
                        if (header) label = header.innerText;
                    }
                }
                if (!label) {
                    label = el.getAttribute('aria-label') || '';
                }
                if (!label) {
                    const ph = el.getAttribute('placeholder') || '';
                    if (!/type your response|enter response|type here|your answer/i.test(ph)) {
                        label = ph;
                    }
                }

                let options = [];
                if (tag === 'select') {
                    options = Array.from(el.options).map(o => o.text.trim()).filter(Boolean);
                }

                const cleanLabel = (label || '').replace(/\\s+/g, ' ').trim();
                if (cleanLabel || elId) {
                    list.push({
                        field_id: elId,
                        label: cleanLabel || elId,
                        field_type: elType,
                        options: options,
                        required: !!required,
                    });
                }
            }
            return list;
        }
        """
        unresolved = await page.evaluate(scan_script) or []
    except Exception as e:
        logger.debug("Failed scanning unresolved fields: %s", e)

    duration_ms = int((time.time() - start_time) * 1000)
    return {
        "filled": filled,
        "unresolved": unresolved,
        "duration_ms": duration_ms,
    }
