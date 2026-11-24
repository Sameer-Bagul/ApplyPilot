"""Unit tests for LeadRanker and Persona Classifier."""

from __future__ import annotations

import sqlite3
import pytest

from applypilot.database import init_db, store_recruiter_lead
from applypilot.outreach.lead_ranker import (
    classify_recipient_persona,
    compute_lead_priority,
    LeadRanker,
)


@pytest.fixture
def test_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def test_classify_recipient_persona():
    # HR Persona
    assert classify_recipient_persona(contact_name="Sarah Smith", contact_email="sarah@acme.com", role_title="Head of Talent Acquisition") == "hr"
    assert classify_recipient_persona(contact_email="careers@startup.io") == "hr"
    assert classify_recipient_persona(contact_email="hr@techcorp.com") == "hr"

    # Founder / Executive Persona
    assert classify_recipient_persona(contact_name="Alex Rivera", contact_email="alex@acme.com", role_title="Co-Founder & CEO") == "founder"
    assert classify_recipient_persona(contact_email="founder@unicorn.ai") == "founder"
    assert classify_recipient_persona(contact_email="cto@deeptech.org") == "founder"

    # Engineering Persona
    assert classify_recipient_persona(contact_name="Bob Chen", contact_email="bob@acme.com", role_title="Staff Software Engineer") == "engineer"
    assert classify_recipient_persona(contact_name="Dev Lead", role_title="VP of Engineering") == "engineer"


def test_compute_lead_priority_scoring():
    # High Priority: Matching open job + tech stack + founder
    lead_high = {
        "contact_email": "founder@agentic.ai",
        "company_domain": "agentic.ai",
        "role_title": "AI Engineer",
        "execution_route": "DUAL_ATTACK",
    }
    intel_high = {
        "official_domain": "agentic.ai",
        "open_roles": [{"title": "Senior AI Engineer", "fit_score": 9}],
        "tech_stack": ["Python", "FastAPI", "React", "Docker"],
        "ai_focus_tags": ["Ai", "Llm"],
    }
    score_high = compute_lead_priority(lead_high, intel_high, ["Python", "React", "FastAPI"])
    assert score_high >= 85

    # Medium Priority: No open role, but tech stack overlap
    lead_mid = {
        "contact_email": "cto@generaltech.com",
        "company_domain": "generaltech.com",
        "role_title": "General Outreach",
    }
    intel_mid = {
        "official_domain": "generaltech.com",
        "open_roles": [],
        "tech_stack": ["Python", "PostgreSQL"],
        "ai_focus_tags": [],
    }
    score_mid = compute_lead_priority(lead_mid, intel_mid, ["Python", "React"])
    assert 40 <= score_mid < 85

    # Invalid / Disqualified: Empty email
    assert compute_lead_priority({"contact_email": ""}, intel_high) == 0


def test_lead_ranker_selection_order(test_db):
    # Seed leads into DB
    store_recruiter_lead(
        company_name="Low Priority Co",
        company_domain="low.com",
        contact_email="info@low.com",
        role_title="Sales Rep",
        execution_route="EMAIL_ONLY",
        conn=test_db,
    )
    store_recruiter_lead(
        company_name="High Priority AI",
        company_domain="highai.com",
        contact_email="founder@highai.com",
        role_title="AI Engineer",
        execution_route="DUAL_ATTACK",
        conn=test_db,
    )

    ranker = LeadRanker(conn=test_db)
    top_picks = ranker.select_daily_top_picks(limit=10, min_score=40)

    assert len(top_picks) >= 1
    # Top pick must be the High Priority AI lead
    assert top_picks[0]["company_name"] == "High Priority AI"
    assert top_picks[0]["persona"] == "founder"
    assert top_picks[0]["priority_score"] > 50

