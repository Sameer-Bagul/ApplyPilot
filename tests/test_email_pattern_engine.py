"""Unit tests for EmailPatternEngine."""

from __future__ import annotations

import pytest

from applypilot.discovery.email_pattern_engine import (
    EmailPatternEngine,
    clean_name_tokens,
    match_name_to_email_pattern,
    render_email,
)


def test_clean_name_tokens():
    assert clean_name_tokens("Arjun Soin") == ("arjun", "soin")
    assert clean_name_tokens("Sarah Connor-Smith") == ("sarah", "connorsmith")
    assert clean_name_tokens("Madonna") == ("madonna", "")
    assert clean_name_tokens("") == ("", "")


def test_render_email_all_canonical_patterns():
    name = "Arjun Soin"
    domain = "clinikally.com"

    assert render_email("{first}.{last}", name, domain) == "arjun.soin@clinikally.com"
    assert render_email("{f}{last}", name, domain) == "asoin@clinikally.com"
    assert render_email("{first}", name, domain) == "arjun@clinikally.com"
    assert render_email("{first}_{last}", name, domain) == "arjun_soin@clinikally.com"
    assert render_email("{first}{l}", name, domain) == "arjuns@clinikally.com"
    assert render_email("{first}{last}", name, domain) == "arjunsoin@clinikally.com"
    assert render_email("{last}.{first}", name, domain) == "soin.arjun@clinikally.com"


def test_match_name_to_email_pattern():
    name = "David Miller"
    assert match_name_to_email_pattern("david.miller", name) == "{first}.{last}"
    assert match_name_to_email_pattern("dmiller", name) == "{f}{last}"
    assert match_name_to_email_pattern("david_miller", name) == "{first}_{last}"
    assert match_name_to_email_pattern("david", name) == "{first}"
    assert match_name_to_email_pattern("random_user", name) is None


def test_deduce_pattern_confirmed_by_known_person():
    engine = EmailPatternEngine()
    emails = ["careers@techcorp.com", "info@techcorp.com", "priya.sharma@techcorp.com"]
    people = [{"name": "Priya Sharma", "role": "Technical Recruiter"}]

    res = engine.deduce_pattern(emails, sample_people=people, domain="techcorp.com")
    assert res["pattern"] == "{first}.{last}"
    assert res["confidence"] == 0.95
    assert "Priya Sharma" in res["evidence"]


def test_deduce_pattern_from_structural_signals():
    engine = EmailPatternEngine()
    emails = ["john.doe@startup.io", "alice.smith@startup.io"]

    res = engine.deduce_pattern(emails, domain="startup.io")
    assert res["pattern"] == "{first}.{last}"
    assert res["confidence"] >= 0.80


def test_apply_pattern_to_people():
    engine = EmailPatternEngine()
    people = [
        {"name": "Arjun Soin", "role": "CEO"},
        {"name": "Priya Sharma", "role": "CTO"},
    ]
    updated = engine.apply_pattern_to_people(people, domain="clinikally.com", pattern="{f}{last}")
    assert updated[0]["email"] == "asoin@clinikally.com"
    assert updated[1]["email"] == "psharma@clinikally.com"
    assert updated[0]["email_pattern"] == "{f}{last}"

