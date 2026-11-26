"""Tests for Levergreen ATS Seed Importer and Deep Email Extractor."""

import pytest
from unittest.mock import MagicMock, patch

from applypilot.discovery.levergreen_importer import import_ats_seeds_to_watchlist
from applypilot.enrichment.crawl4ai_extractor import (
    is_valid_email,
    classify_contact_type,
    deep_crawl_company_domain,
)
from applypilot.discovery.jobspy import _location_ok


def test_location_ok_accepts_india_and_remote():
    accept = ["Remote", "Bangalore", "Pune", "India"]
    reject = ["onsite only"]

    # Remote should always be accepted
    assert _location_ok("Remote - Anywhere", accept, reject) is True
    assert _location_ok("Fully Remote", accept, reject) is True

    # India cities
    assert _location_ok("Bengaluru, Karnataka, India", accept, reject) is True
    assert _location_ok("Pune, MH", accept, reject) is True

    # Rejections
    assert _location_ok("London onsite only", accept, reject) is False


def test_is_valid_email_filtering():
    assert is_valid_email("talent@supabase.com", "supabase.com") is True
    assert is_valid_email("founder@mistral.ai", "mistral.ai") is True

    # Junk assets and bad extensions
    assert is_valid_email("logo@supabase.com.png", "supabase.com") is False
    assert is_valid_email("image@example.com", "example.com") is False
    assert is_valid_email("support@stripe.com", "stripe.com") is False

    # External trackers
    assert is_valid_email("tracker@google-analytics.com", "stripe.com") is False


def test_classify_contact_type():
    assert classify_contact_type("ceo", "Chief Executive Officer") == "founder"
    assert classify_contact_type("talent", "Senior Recruiter") == "talent_acquisition"
    assert classify_contact_type("hr", "People Partner") == "hr"
    assert classify_contact_type("info", "General queries") == "company_contact"


def test_import_ats_seeds_curated():
    res = import_ats_seeds_to_watchlist(
        include_curated=True,
        include_remote=False,
        poll_now=False,
        limit=5,
    )
    assert res["companies_imported"] == 5
    assert res["companies_total_evaluated"] == 5
