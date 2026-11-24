"""Unit tests for non-login LinkedIn People Finder and Dual-Attack integration."""

from __future__ import annotations

import io
import json
import sqlite3
import urllib.request
from unittest.mock import MagicMock, patch

import pytest

from applypilot.database import (
    get_company_intel,
    init_db,
    save_company_intel,
    store_recruiter_lead,
)
from applypilot.discovery.company_intel_service import CompanyIntelService
from applypilot.discovery.linkedin_people_finder import (
    LinkedInPeopleFinder,
    classify_persona_from_role,
    extract_linkedin_id,
    find_company_people_sync,
    generate_linkedin_connection_note,
)


@pytest.fixture
def test_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def test_extract_linkedin_id():
    assert extract_linkedin_id("https://www.linkedin.com/in/arjun-soin-97a568114/") == "arjun-soin-97a568114"
    assert extract_linkedin_id("https://in.linkedin.com/in/sarah-connor?trk=public") == "sarah-connor"
    assert extract_linkedin_id("http://linkedin.com/in/alex_dev_99") == "alex_dev_99"
    assert extract_linkedin_id("https://google.com/search") is None
    assert extract_linkedin_id("") is None
    assert extract_linkedin_id(None) is None


def test_classify_persona_from_role():
    assert classify_persona_from_role("Co-Founder & CEO") == "founder"
    assert classify_persona_from_role("Founder & CTO") == "founder"
    assert classify_persona_from_role("Head of Talent & Recruiting") == "hr"
    assert classify_persona_from_role("Senior Technical Recruiter") == "hr"
    assert classify_persona_from_role("VP of Engineering") == "engineer"
    assert classify_persona_from_role("Lead Software Architect") == "engineer"
    assert classify_persona_from_role("Unknown Executive") == "founder"


def test_generate_linkedin_connection_note_length_and_angles():
    # Founder angle
    note_founder = generate_linkedin_connection_note(
        person_name="Arjun Soin",
        role="Founder / CEO",
        company="Clinikally",
        candidate_skills=["Python", "FastAPI", "React", "AI"],
    )
    assert len(note_founder) <= 300
    assert "Arjun" in note_founder
    assert "Clinikally" in note_founder
    assert "Python/FastAPI" in note_founder

    # HR angle
    note_hr = generate_linkedin_connection_note(
        person_name="Priya Sharma",
        role="Technical Recruiter",
        company="TechCorp",
        candidate_skills=["TypeScript", "Next.js"],
    )
    assert len(note_hr) <= 300
    assert "Priya" in note_hr
    assert "talent focus" in note_hr

    # Engineer angle
    note_eng = generate_linkedin_connection_note(
        person_name="David Miller",
        role="Head of Engineering",
        company="CloudScale",
        candidate_skills=["Rust", "Kubernetes"],
    )
    assert len(note_eng) <= 300
    assert "David" in note_eng
    assert "fellow engineer" in note_eng


def test_yc_directory_extraction_mocked(test_db):
    finder = LinkedInPeopleFinder(conn=test_db)

    # HTML responses for company page and founder page
    company_html = """
    <html>
        <body>
            <a href="/founders/480320-arjun-soin">Arjun Soin</a>
        </body>
    </html>
    """.encode("utf-8")

    founder_html = """
    <html>
        <head><title>Y Combinator</title></head>
        <body>
            <h1 class="text-2xl">Arjun Soin</h1>
            <a href="https://www.linkedin.com/in/arjun-soin-97a568114/">LinkedIn Profile</a>
        </body>
    </html>
    """.encode("utf-8")

    def mock_urlopen(req, timeout=5):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        mock_resp = MagicMock()
        mock_resp.status = 200
        if "/companies/" in url:
            mock_resp.read.return_value = company_html
        elif "/founders/" in url:
            mock_resp.read.return_value = founder_html
        mock_resp.__enter__.return_value = mock_resp
        return mock_resp

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        people = finder.find_people_for_company(
            company_name="Clinikally",
            domain="clinikally.com",
            candidate_skills=["Python", "React"],
        )

    assert len(people) >= 1
    p = people[0]
    assert p["name"] == "Arjun Soin"
    assert p["role"] == "Founder / CEO"
    assert p["linkedin_id"] == "arjun-soin-97a568114"
    assert "linkedin.com/in/arjun-soin-97a568114" in p["linkedin_url"]
    assert len(p["connection_note"]) <= 300

    # Verify persistence into recruiter_leads with DUAL_ATTACK
    rows = test_db.execute(
        "SELECT * FROM recruiter_leads WHERE LOWER(company_name) = 'clinikally'"
    ).fetchall()
    assert len(rows) >= 1
    assert rows[0]["contact_name"] == "Arjun Soin"
    assert rows[0]["execution_route"] == "DUAL_ATTACK"
    assert rows[0]["contact_linkedin_url"] == "https://www.linkedin.com/in/arjun-soin-97a568114"

    # Verify persistence into company_intel table
    intel = get_company_intel("clinikally.com", conn=test_db)
    assert intel is not None
    assert intel["key_people_json"] is not None
    key_people = json.loads(intel["key_people_json"])
    assert key_people[0]["name"] == "Arjun Soin"


def test_company_intel_service_integrates_people(test_db):
    service = CompanyIntelService(conn=test_db)

    with patch("applypilot.discovery.company_intel_service.investigate_company_wikipedia") as mock_wiki, \
         patch("applypilot.discovery.company_intel_service.investigate_company_github_projects") as mock_gh, \
         patch("applypilot.discovery.linkedin_people_finder.LinkedInPeopleFinder.find_people_for_company") as mock_finder:

        mock_wiki.return_value = {"found": False}
        mock_gh.return_value = []
        mock_finder.return_value = [
            {
                "name": "Jane Founder",
                "role": "Founder / CEO",
                "persona": "founder",
                "linkedin_url": "https://www.linkedin.com/in/janefounder",
                "linkedin_id": "janefounder",
                "connection_note": "Hi Jane, love what you're doing!",
                "source": "test_mock",
            }
        ]

        intel = service.get_or_research("Acme Startup", domain="acmestartup.com")
        assert intel["company_name"] == "Acme Startup"
        assert len(intel["key_people"]) == 1
        assert intel["key_people"][0]["name"] == "Jane Founder"
        assert intel["key_people"][0]["linkedin_id"] == "janefounder"

