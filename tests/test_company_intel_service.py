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
         patch("applypilot.discovery.company_intel_service.investigate_company_github_projects") as mock_gh:

        mock_wiki.return_value = {
            "found": True,
            "title": "Acme AI Corp",
            "summary": "Acme AI builds autonomous agent systems and neural networks.",
        }
        mock_gh.return_value = [
            {"name": "agent-core", "description": "Core LangGraph agent runner", "language": "Python"}
        ]

        # 1. First call: Cache miss -> calls external APIs
        intel1 = service.get_or_research("Acme AI", domain="acme.ai")
        assert intel1["company_name"] == "Acme AI"
        assert "Python" in intel1["tech_stack"]
        assert mock_wiki.call_count == 1
        assert mock_gh.call_count == 1

        # 2. Second call: Cache hit -> does NOT call APIs again
        intel2 = service.get_or_research("Acme AI", domain="acme.ai")
        assert intel2["company_name"] == "Acme AI"
        assert "Python" in intel2["tech_stack"]
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
         patch("applypilot.discovery.company_intel_service.investigate_company_github_projects") as mock_gh:

        mock_wiki.return_value = {"found": False}
        mock_gh.return_value = []

        intel_map = service.enrich_batch_for_leads(leads)

        # 3 leads across 2 unique companies -> exactly 2 research executions
        assert mock_wiki.call_count == 2
        assert "acme.com" in intel_map
        assert "betalabs.io" in intel_map

