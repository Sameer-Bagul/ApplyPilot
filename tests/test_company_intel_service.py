"""Unit tests for CompanyIntelService and 30-day SQLite caching."""

from __future__ import annotations

import sqlite3
import pytest
from unittest.mock import patch, MagicMock

from applypilot.database import init_db
from applypilot.discovery.company_intel_service import (
    CompanyIntelService,
    _detect_ai_focus,
)


@pytest.fixture
def test_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def test_detect_ai_focus():
    tags = _detect_ai_focus("We build scalable LLM agents with RAG pipelines.", ["Python", "FastAPI"])
    assert "Llm" in tags or "Agent" in tags or "Rag" in tags

    empty_tags = _detect_ai_focus("We manufacture plastic pipes and fittings.", ["Java"])
    assert len(empty_tags) == 0


def test_company_intel_caching_and_deduplication(test_db):
    service = CompanyIntelService(conn=test_db)

    # Mock external APIs
    with patch("applypilot.discovery.company_intel_service.investigate_company_wikipedia") as mock_wiki, \
         patch("applypilot.discovery.company_intel_service.investigate_company_github_projects") as mock_gh, \
         patch("applypilot.discovery.linkedin_people_finder.find_company_people_sync") as mock_people, \
         patch("applypilot.discovery.deep_web_searcher.DeepWebSearcher.search_and_analyze_company") as mock_deep, \
         patch("applypilot.discovery.social_hiring_harvester.SocialHiringHarvester.harvest_company_hiring_posts") as mock_social:

        mock_wiki.return_value = {
            "found": True,
            "title": "Acme AI Corp",
            "summary": "Acme AI builds autonomous agent systems and neural networks.",
        }
        mock_gh.return_value = [
            {"name": "agent-core", "description": "Core LangGraph agent runner", "language": "Python"}
        ]
        mock_people.return_value = [
            {"name": "Alice Smith", "role": "CEO", "persona": "founder", "linkedin_url": "https://linkedin.com/in/alicesmith"}
        ]
        mock_deep.return_value = {
            "articles_checked": 2,
            "discovered_emails": ["alice.smith@acme.ai"],
            "discovered_leaders": [],
            "company_milestones": ["Raised $10M Series A"],
        }
        mock_social.return_value = [
            {
                "platform": "linkedin_post",
                "author_name": "Alice Smith",
                "post_url": "https://linkedin.com/posts/alice-hiring",
                "post_quote": "We're hiring senior AI engineers!",
                "embedded_emails": ["alice.smith@acme.ai"],
                "evidence_snippet": "Found on LinkedIn Post",
            }
        ]

        # 1. First call: Cache miss -> calls external APIs
        intel1 = service.get_or_research("Acme AI", domain="acme.ai")
        assert intel1["company_name"] == "Acme AI"
        assert "Python" in intel1["tech_stack"]
        assert intel1["detected_email_pattern"] == "{first}.{last}"
        assert intel1["email_pattern_confidence"] >= 0.85
        assert len(intel1["hiring_posts"]) == 1
        assert intel1["key_people"][0]["email"] == "alice.smith@acme.ai"
        assert mock_wiki.call_count == 1
        assert mock_gh.call_count == 1

        # 2. Second call: Cache hit -> does NOT call APIs again
        intel2 = service.get_or_research("Acme AI", domain="acme.ai")
        assert intel2["company_name"] == "Acme AI"
        assert "Python" in intel2["tech_stack"]
        assert intel2["detected_email_pattern"] == "{first}.{last}"
        assert len(intel2["hiring_posts"]) == 1
        # Call counts remain 1 (0 duplicate API requests)
        assert mock_wiki.call_count == 1
        assert mock_gh.call_count == 1


def test_enrich_batch_for_leads(test_db):
    service = CompanyIntelService(conn=test_db)

    leads = [
        {"lead_id": "1", "company_name": "Acme Corp", "company_domain": "acme.com", "contact_email": "hr@acme.com"},
        {"lead_id": "2", "company_name": "Acme Corp", "company_domain": "acme.com", "contact_email": "founder@acme.com"},
        {"lead_id": "3", "company_name": "Beta Labs", "company_domain": "betalabs.io", "contact_email": "dev@betalabs.io"},
    ]

    with patch("applypilot.discovery.company_intel_service.investigate_company_wikipedia") as mock_wiki, \
         patch("applypilot.discovery.company_intel_service.investigate_company_github_projects") as mock_gh, \
         patch("applypilot.discovery.linkedin_people_finder.find_company_people_sync") as mock_people, \
         patch("applypilot.discovery.deep_web_searcher.DeepWebSearcher.search_and_analyze_company") as mock_deep, \
         patch("applypilot.discovery.social_hiring_harvester.SocialHiringHarvester.harvest_company_hiring_posts") as mock_social:

        mock_wiki.return_value = {"found": False}
        mock_gh.return_value = []
        mock_people.return_value = []
        mock_deep.return_value = {"articles_checked": 0, "discovered_emails": [], "discovered_leaders": [], "company_milestones": []}
        mock_social.return_value = []

        intel_map = service.enrich_batch_for_leads(leads)

        # 3 leads across 2 unique companies -> exactly 2 research executions
        assert mock_wiki.call_count == 2
        assert "acme.com" in intel_map
        assert "betalabs.io" in intel_map
