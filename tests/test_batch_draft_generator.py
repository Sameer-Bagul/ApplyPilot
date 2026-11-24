"""Unit tests for BatchDraftGenerator and outreach execution."""

from __future__ import annotations

import json
import sqlite3
import pytest
from unittest.mock import patch, MagicMock

from applypilot.database import init_db, store_recruiter_lead
from applypilot.outreach.batch_draft_generator import (
    BatchDraftGenerator,
    _generate_fallback_draft,
)
from applypilot.outreach.mailer import run_top_pick_outreach


@pytest.fixture
def test_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def test_fallback_draft_generation():
    candidate = {
        "name": "Sameer Bagul",
        "email": "sameer@example.com",
        "notice_period": "Immediate",
        "urls": {"github": "https://github.com/test", "linkedin": "https://linkedin.com/test"},
    }

    # Test HR Fallback Draft
    hr_lead = {
        "lead_id": "lead_01",
        "contact_name": "Jane Doe",
        "contact_email": "jane@acme.com",
        "company_name": "Acme",
        "role_title": "AI Engineer",
        "persona": "hr",
        "company_intel": {"tech_stack": ["Python", "FastAPI"]},
    }
    hr_draft = _generate_fallback_draft(hr_lead, candidate)
    assert hr_draft["lead_id"] == "lead_01"
    assert "Notice Period: Immediate" in hr_draft["body_text"]
    assert "resume (PDF)" in hr_draft["body_text"]

    # Test Founder Fallback Draft
    founder_lead = {
        "lead_id": "lead_02",
        "contact_name": "Elon Musk",
        "contact_email": "elon@x.ai",
        "company_name": "xAI",
        "role_title": "Distributed Systems",
        "persona": "founder",
        "company_intel": {"tech_stack": ["Rust", "Python"]},
    }
    founder_draft = _generate_fallback_draft(founder_lead, candidate)
    assert founder_draft["lead_id"] == "lead_02"
    assert "Athena" in founder_draft["body_text"]
    assert "10 minutes" in founder_draft["body_text"]


def test_batch_draft_generator_with_llm_mock():
    generator = BatchDraftGenerator(batch_size=5)

    sample_leads = [
        {
            "lead_id": "lead_100",
            "contact_name": "Alice",
            "contact_email": "alice@deeptech.com",
            "company_name": "DeepTech",
            "role_title": "Senior AI Engineer",
            "persona": "founder",
            "company_intel": {"tech_stack": ["Python", "LangGraph"]},
        }
    ]

    mock_llm_response = json.dumps({
        "drafts": [
            {
                "lead_id": "lead_100",
                "subject": "DeepTech + AI Systems // Sameer Bagul",
                "body_text": "Hi Alice, Loved DeepTech's recent work...",
                "body_html": "<p>Hi Alice, Loved DeepTech's recent work...</p>",
                "cta": "Let's connect for 10 minutes.",
                "match_reason": "Matched LangGraph and Python stack",
            }
        ]
    })

    with patch("applypilot.outreach.batch_draft_generator.get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.chat.return_value = mock_llm_response
        mock_get_client.return_value = mock_client

        drafts = generator.generate_drafts_for_leads(sample_leads)
        assert len(drafts) == 1
        assert drafts[0]["lead_id"] == "lead_100"
        assert drafts[0]["subject"] == "DeepTech + AI Systems // Sameer Bagul"


def test_run_top_pick_outreach_dry_run(test_db):
    store_recruiter_lead(
        company_name="Apex Robotics",
        company_domain="apexrobotics.com",
        contact_email="cto@apexrobotics.com",
        role_title="AI Robotics Engineer",
        execution_route="EMAIL_ONLY",
        conn=test_db,
    )

    with patch("applypilot.outreach.batch_draft_generator.get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.chat.side_effect = Exception("LLM offline")
        mock_get_client.return_value = mock_client

        res = run_top_pick_outreach(limit=5, min_score=40, dry_run=True, conn=test_db)
        assert res["total_selected"] >= 1
        assert len(res["leads"]) >= 1
        assert res["leads"][0]["status"] == "dry_run"
        assert res["leads"][0]["email"] == "cto@apexrobotics.com"

