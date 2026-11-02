"""Unit tests for Bangalore Startup Map Harvester, VIP Watchlist, and LinkedIn Note Generator."""

import json
import sqlite3
import pytest

from applypilot.discovery.bangalore_map_harvester import (
    generate_linkedin_connection_note,
    parse_bangalore_map_rsc,
    import_bangalore_startups_to_watchlist,
)
from applypilot.database import (
    get_career_watchlist,
    get_recruiter_leads,
    init_db,
)


MOCK_RSC_PAYLOAD = r"""
<!DOCTYPE html><html><body>
<script>self.__next_f.push([1, "1:HL[\"/_next/static/css/app.css\",\"style\"]\n"])</script>
<script>self.__next_f.push([1, "6:{\"startups\":[{\"name\":\"NeuralScale AI\",\"slug\":\"neuralscale\",\"kind\":\"startup\",\"tagline\":\"Enterprise LLM infrastructure\",\"description\":\"Building scalable reasoning agents for finance.\",\"stage\":\"Series A\",\"sector\":\"AI\",\"tags\":[\"ai\",\"llm\",\"infrastructure\"],\"area\":\"HSR Layout\",\"hsr_location\":\"HSR Sector 4\",\"website\":\"https://neuralscale.ai\",\"founders\":\"Arjun Mehta, Neha Sharma\",\"founder_links\":[{\"name\":\"Arjun Mehta\",\"url\":\"https://in.linkedin.com/in/arjunmehta\"}],\"founded_year\":2023},{\"name\":\"FinPulse\",\"slug\":\"finpulse\",\"kind\":\"startup\",\"tagline\":\"Instant cross-border treasury\",\"description\":\"Payments infrastructure for exporters.\",\"stage\":\"Seed\",\"sector\":\"Fintech\",\"tags\":[\"fintech\",\"payments\"],\"area\":\"Koramangala\",\"hsr_location\":\"Koramangala 5th Block\",\"website\":\"https://finpulse.co\",\"founders\":\"Rahul Verma\",\"founder_links\":[],\"founded_year\":2022}],\"roles\":{\"neuralscale\":[{\"track\":\"engineering\",\"seniority\":\"senior\",\"fresher_friendly\":false,\"posted_day\":20755}]},\"roleKeywords\":{\"neuralscale\":[\"agent\",\"python\",\"distributed\"]},\"hiringAvailable\":true}\n"])</script>
</body></html>
"""


def test_parse_bangalore_map_rsc():
    startups, roles, role_keywords = parse_bangalore_map_rsc(MOCK_RSC_PAYLOAD)

    assert len(startups) == 2
    assert startups[0]["name"] == "NeuralScale AI"
    assert startups[0]["slug"] == "neuralscale"
    assert startups[0]["sector"] == "AI"
    assert startups[0]["stage"] == "Series A"
    assert startups[0]["area"] == "HSR Layout"
    assert startups[0]["is_hiring"] is True
    assert startups[0]["open_roles_count"] == 1
    assert "neuralscale" in roles
    assert "agent" in role_keywords["neuralscale"]

    assert startups[1]["name"] == "FinPulse"
    assert startups[1]["is_hiring"] is False
    assert startups[1]["open_roles_count"] == 0


def test_generate_linkedin_connection_note_length_and_content():
    note = generate_linkedin_connection_note(
        founder_name="Arjun Mehta",
        startup_name="NeuralScale AI",
        sector="AI",
        tagline="Enterprise LLM infrastructure",
    )
    assert len(note) <= 280
    assert "Arjun" in note
    assert "NeuralScale AI" in note
    assert "AI" in note

    # Test long names and fallbacks
    long_note = generate_linkedin_connection_note(
        founder_name="Dr. Bartholomew Alexander Montgomery III",
        startup_name="Supercalifragilisticexpialidocious Ultra Global Technologies Private Limited",
        sector="Advanced Quantum Cybernetics and Autonomous Nanorobotic Systems",
        tagline="A " * 200,
    )
    assert len(long_note) <= 280


def test_import_bangalore_startups_with_mock_rsc(monkeypatch, tmp_path):
    # Setup test SQLite DB
    db_file = tmp_path / "test_blr.db"
    conn = init_db(db_file)

    # Monkeypatch fetch_bangalore_map_raw to return mock RSC payload
    import applypilot.discovery.bangalore_map_harvester as harvester
    monkeypatch.setattr(harvester, "fetch_bangalore_map_raw", lambda *args, **kwargs: MOCK_RSC_PAYLOAD)
    # Monkeypatch deep profile fetch
    monkeypatch.setattr(
        harvester,
        "fetch_company_deep_profile",
        lambda slug, **kwargs: {
            "slug": slug,
            "profile_url": f"https://www.bangalorestartupmap.com/company/{slug}",
            "website": "https://neuralscale.ai" if slug == "neuralscale" else "https://finpulse.co",
            "ats_links": ["https://jobs.lever.co/neuralscale/senior-agent-engineer"] if slug == "neuralscale" else [],
            "company_linkedin": f"https://www.linkedin.com/company/{slug}",
            "founder_linkedins": ["https://in.linkedin.com/in/arjunmehta"] if slug == "neuralscale" else [],
            "careers_url": "https://neuralscale.ai/careers",
        },
    )
    # Monkeypatch email enricher
    monkeypatch.setattr(
        harvester,
        "enrich_startup_website_emails",
        lambda website, **kwargs: ["careers@neuralscale.ai", "talent@neuralscale.ai"] if "neuralscale" in website else [],
    )

    result = import_bangalore_startups_to_watchlist(
        sectors=["AI"],
        only_hiring=False,
        limit=10,
        fetch_deep=True,
        dry_run=False,
        conn=conn,
    )

    assert result["status"] == "success"
    assert result["imported_companies"] == 1
    assert result["open_roles_indexed"] >= 1
    assert result["recruiter_leads_created"] >= 1

    # Verify career_watchlist
    watchlist = get_career_watchlist(conn=conn)
    assert len(watchlist) == 1
    w = watchlist[0]
    assert w["company_name"] == "NeuralScale AI"
    assert w["priority_tier"] == 1
    assert w["is_vip"] == 1
    assert w["sector"] == "AI"
    assert w["area"] == "HSR Layout"
    assert "lever" in (w["ats_provider"] or "")

    # Verify recruiter leads
    leads = get_recruiter_leads(conn=conn)
    assert len(leads) >= 1
    founder_lead = next((l for l in leads if l.get("contact_linkedin_url")), None)
    assert founder_lead is not None
    assert founder_lead["contact_linkedin_url"] == "https://in.linkedin.com/in/arjunmehta"
    assert founder_lead["linkedin_connection_note"] is not None
    assert len(founder_lead["linkedin_connection_note"]) <= 280
