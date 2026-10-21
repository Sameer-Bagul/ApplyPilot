"""Unit tests for Tier 0 Playbook (ATS detection and field mappings)."""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from applypilot.database import init_db, store_selector
from applypilot.learning.tier0_playbook import (
    detect_form_ats,
    get_tier0_field_mappings,
    _resolve_profile_value,
)


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_tier0.db"
    conn = init_db(db_file)
    return conn


def test_detect_form_ats_by_url():
    assert detect_form_ats("https://job-boards.greenhouse.io/databricks/jobs/1234") == "greenhouse"
    assert detect_form_ats("https://boards.greenhouse.io/acme/jobs/5678") == "greenhouse"
    assert detect_form_ats("https://jobs.lever.co/stripe/abcdef") == "lever"
    assert detect_form_ats("https://acme.myworkdayjobs.com/en-US/Careers/job/123") == "workday"
    assert detect_form_ats("https://jobs.ashbyhq.com/statsig/xyz") == "ashby"
    assert detect_form_ats("https://careers.company.com/apply/123") == "custom_domain"


def test_detect_form_ats_by_html_snippet():
    assert detect_form_ats("https://careers.company.com", html_snippet="<iframe src='https://boards.greenhouse.io/embed'>") == "greenhouse"
    assert detect_form_ats("https://careers.company.com", html_snippet="<div data-automation-id='workdayApplication'>") == "workday"


def test_resolve_profile_value():
    profile = {
        "first_name": "Sameer",
        "last_name": "Bagul",
        "contact": {
            "email": "sameer@example.com",
            "phone": "+1-555-0123",
        },
        "links": {
            "linkedin": "https://linkedin.com/in/sameerbagul",
        },
    }

    assert _resolve_profile_value("profile.first_name", profile) == "Sameer"
    assert _resolve_profile_value("profile.full_name", profile) == "Sameer Bagul"
    assert _resolve_profile_value("profile.contact.email", profile) == "sameer@example.com"
    assert _resolve_profile_value("profile.links.linkedin", profile) == "https://linkedin.com/in/sameerbagul"
    assert _resolve_profile_value("profile.nonexistent", profile) is None


def test_get_tier0_field_mappings_includes_baseline_and_cached(test_db):
    # Store a learned selector in database cache
    store_selector(
        ats_type="greenhouse",
        domain_pattern="job-boards.greenhouse.io",
        css_or_aria_selector="input#custom_linkedin_field",
        action_type="fill",
        target_key="profile.linkedin_url",
        conn=test_db,
    )

    mappings = get_tier0_field_mappings("greenhouse", "job-boards.greenhouse.io", conn=test_db)
    assert len(mappings) > 0

    # The cached selector should be prioritized
    cached_mappings = [m for m in mappings if m["source"] == "cache"]
    assert len(cached_mappings) == 1
    assert cached_mappings[0]["selector"] == "input#custom_linkedin_field"
    assert cached_mappings[0]["target_key"] == "profile.linkedin_url"

    # Baseline selectors should cover first_name, email, resume_file
    keys = {m["target_key"] for m in mappings}
    assert "profile.first_name" in keys
    assert "profile.email" in keys
    assert "resume_file" in keys
