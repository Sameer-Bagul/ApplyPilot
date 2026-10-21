"""Unit tests for Tier 2 Heuristics (phone, date, unit conversions)."""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from applypilot.learning.tier2_heuristics import (
    normalize_phone,
    format_date,
    sanitize_url,
    transform_units,
)


def test_normalize_phone():
    # US standard 10 digits
    assert normalize_phone("5551234567", format_style="e164") == "+15551234567"
    assert normalize_phone("(555) 123-4567", format_style="dashed") == "555-123-4567"
    assert normalize_phone("555.123.4567", format_style="national") == "(555) 123-4567"
    assert normalize_phone("555-123-4567", format_style="digits") == "5551234567"

    # US 11 digits with leading 1
    assert normalize_phone("15551234567", format_style="national") == "(555) 123-4567"

    # International phone with +
    assert normalize_phone("+91-9876543210", format_style="e164") == "+919876543210"
    assert normalize_phone("+91-9876543210", format_style="digits") == "919876543210"


def test_format_date():
    # ISO to US MM/DD/YYYY
    assert format_date("2024-05-20", "MM/DD/YYYY") == "05/20/2024"
    # US to ISO YYYY-MM-DD
    assert format_date("05/20/2024", "YYYY-MM-DD") == "2024-05-20"
    # Month/Year
    assert format_date("2024-05", "MM/YYYY") == "05/2024"


def test_sanitize_url():
    assert sanitize_url("github.com/sameer") == "https://github.com/sameer"
    assert sanitize_url("https://linkedin.com/in/sameer") == "https://linkedin.com/in/sameer"
    assert sanitize_url("http://myportfolio.dev") == "http://myportfolio.dev"


def test_transform_units():
    # Years to months
    assert transform_units("5", "val * 12") == 60.0
    assert transform_units("5 years", "val * 12") == 60.0
    assert transform_units(3.5, "val * 12") == 42.0
