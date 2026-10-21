"""Tier 2: Learned Heuristic & Regex Rule Engine.

Applies deterministic post-run formatting rules: phone normalization,
date format conversion, unit scaling (e.g. years to months), and URL protocol
sanitization without LLM tokens.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def normalize_phone(phone: str, country_code: str = "+1",
                    format_style: str = "e164") -> str:
    """Normalize phone numbers according to ATS requirements.

    Args:
        phone: Raw phone string (e.g. "555-123-4567" or "+91 9876543210").
        country_code: Default international prefix if missing.
        format_style: 'e164' (+15551234567), 'national' ((555) 123-4567),
                     'dashed' (555-123-4567), or 'digits' (5551234567).
    """
    if not phone:
        return ""

    raw = str(phone).strip()
    has_plus = raw.startswith("+")
    digits = re.sub(r"[^\d]", "", raw)

    if not digits:
        return ""

    # If international prefix is present
    if has_plus:
        if format_style == "e164":
            return f"+{digits}"
        if format_style == "digits":
            return digits

    # If 10 digits (standard US/India national number without country code)
    if len(digits) == 10:
        if format_style == "e164":
            prefix = country_code if country_code.startswith("+") else f"+{country_code}"
            return f"{prefix}{digits}"
        if format_style == "national":
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        if format_style == "dashed":
            return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
        if format_style == "digits":
            return digits

    # If 11 digits starting with 1 (US with leading 1)
    if len(digits) == 11 and digits.startswith("1"):
        if format_style == "e164":
            return f"+{digits}"
        if format_style == "national":
            return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        if format_style == "dashed":
            return f"{digits[1:4]}-{digits[4:7]}-{digits[7:]}"
        if format_style == "digits":
            return digits[1:]

    # Fallback to E.164 if plus was present, else digits
    return f"+{digits}" if has_plus else digits


def format_date(date_str: str, target_format: str = "MM/DD/YYYY") -> str:
    """Convert common date strings into requested ATS format.

    Supports formats like 'YYYY-MM-DD', 'MM/DD/YYYY', 'DD/MM/YYYY', 'Month YYYY'.
    """
    if not date_str:
        return ""

    raw = date_str.strip()
    parts = re.split(r"[-/\s.]+", raw)

    year, month, day = None, None, None

    # Pattern: YYYY-MM-DD
    if len(parts) >= 3 and len(parts[0]) == 4:
        year, month, day = parts[0], parts[1].zfill(2), parts[2].zfill(2)
    # Pattern: MM/DD/YYYY or DD/MM/YYYY
    elif len(parts) >= 3 and len(parts[2]) == 4:
        year = parts[2]
        # Heuristic: if first part > 12, it must be DD/MM
        p1, p2 = int(parts[0]), int(parts[1])
        if p1 > 12:
            day, month = str(p1).zfill(2), str(p2).zfill(2)
        else:
            month, day = str(p1).zfill(2), str(p2).zfill(2)
    elif len(parts) == 2:
        if len(parts[0]) == 4:
            year, month = parts[0], parts[1].zfill(2)
        elif len(parts[1]) == 4:
            month, year = parts[0].zfill(2), parts[1]
        day = "01"

    if not (year and month):
        return raw

    tf = target_format.upper()
    if tf == "MM/DD/YYYY":
        return f"{month}/{day or '01'}/{year}"
    if tf == "YYYY-MM-DD":
        return f"{year}-{month}-{day or '01'}"
    if tf == "DD/MM/YYYY":
        return f"{day or '01'}/{month}/{year}"
    if tf in {"MM/YYYY", "MM/YY"}:
        y_out = year if tf == "MM/YYYY" else year[-2:]
        return f"{month}/{y_out}"

    return raw


def sanitize_url(url: str) -> str:
    """Ensure URL has http/https protocol."""
    if not url:
        return ""
    clean = url.strip()
    if not re.match(r"^https?://", clean, re.IGNORECASE):
        clean = f"https://{clean}"
    return clean


def transform_units(value: Any, transform_expression: str) -> Any:
    """Safely apply a unit scaling expression (e.g. 'val * 12' or 'int(val)')."""
    if value is None:
        return None
    try:
        # Extract numeric value
        if isinstance(value, str):
            num_match = re.search(r"[-+]?\d*\.?\d+", value)
            val = float(num_match.group(0)) if num_match else 0
        else:
            val = float(value)

        # Restricted eval for basic math expressions only
        safe_expr = re.sub(r"[^0-9\.\+\-\*\/\(\)\s]", "", transform_expression.replace("val", str(val)))
        if safe_expr:
            # Evaluates only arithmetic
            return eval(safe_expr, {"__builtins__": {}})
    except Exception as e:
        logger.debug("Failed to evaluate unit transform '%s' on %s: %s", transform_expression, value, e)
    return value
