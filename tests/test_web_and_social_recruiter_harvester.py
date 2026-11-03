"""Unit tests for Web & Social Recruiter Discovery Harvester and Drill-Down features."""

from __future__ import annotations

import sqlite3
import pytest

from applypilot.discovery.web_and_social_recruiter_harvester import (
    clean_watchlist_domains,
    synthesize_recruiter_emails,
    enrich_company_deep,
    loop_and_enrich_all_watchlist_deep,
)
from applypilot.learning.migrations import run_migrations
from applypilot.database import init_db


@pytest.fixture
def mock_db(tmp_path):
    """In-memory or temporary SQLite database initialized with migrations."""
    db_file = tmp_path / "test_applypilot.db"
    init_db(db_path=db_file)
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    run_migrations(db_path=conn)
    yield conn
    conn.close()


def test_clean_watchlist_domains(mock_db):
    """Verify that known domain overrides and malformed domains are normalized."""
    mock_db.execute(
        """
        INSERT INTO career_watchlist (company_id, company_name, official_domain, careers_page_url)
        VALUES ('comp_1', 'Cloudflare', 'greenhouse', 'https://cloudflare.com/careers'),
               ('comp_2', 'Figma', 'greenhouse', 'https://figma.com/careers'),
               ('comp_3', 'Airbus India', 'airbus.com', 'https://airbus.com')
        """
    )
    mock_db.commit()

    cleaned = clean_watchlist_domains(conn=mock_db)
    assert cleaned >= 2

    c1 = mock_db.execute("SELECT official_domain FROM career_watchlist WHERE company_id = 'comp_1'").fetchone()
    assert c1["official_domain"] == "cloudflare.com"

    c2 = mock_db.execute("SELECT official_domain FROM career_watchlist WHERE company_id = 'comp_2'").fetchone()
    assert c2["official_domain"] == "figma.com"


def test_synthesize_recruiter_emails_and_inboxes():
    """Verify synthesis of personal recruiter emails and standard functional inboxes."""
    recruiters = [
        {
            "name": "Sarah Miller",
            "role": "Lead Technical Recruiter at TechCorp",
            "linkedin_url": "https://linkedin.com/in/sarahmiller",
            "snippet": "Technical recruiter hiring senior engineers",
        }
    ]

    leads = synthesize_recruiter_emails(
        company_name="TechCorp",
        domain="techcorp.io",
        recruiters=recruiters,
        target_count=10,
        check_mx=False,
    )

    emails = [l["email"] for l in leads]
    assert "sarah.miller@techcorp.io" in emails
    assert "careers@techcorp.io" in emails
    assert "talent@techcorp.io" in emails
    assert "hiring@techcorp.io" in emails
    assert "founders@techcorp.io" in emails
    assert len(leads) >= 8


def test_enrich_company_deep(mock_db, monkeypatch):
    """Verify enrichment stores recruiter leads and updates career_watchlist."""
    mock_db.execute(
        """
        INSERT INTO career_watchlist (company_id, company_name, official_domain, careers_page_url)
        VALUES ('comp_test', 'AcmeTech', 'acmetech.com', 'https://acmetech.com/careers')
        """
    )
    mock_db.commit()

    # Mock search_web_recruiters to avoid external network during unit test
    def mock_search(c_name, max_results=4):
        return [
            {
                "name": "Alex Mercer",
                "role": f"Head of Talent at {c_name}",
                "linkedin_url": "https://linkedin.com/in/alexmercer",
                "snippet": "Talent leader hiring engineers",
            }
        ]

    monkeypatch.setattr(
        "applypilot.discovery.web_and_social_recruiter_harvester.search_web_recruiters",
        mock_search,
    )
    # Mock MX check
    monkeypatch.setattr(
        "applypilot.discovery.web_and_social_recruiter_harvester.check_domain_mx",
        lambda domain: True,
    )

    res = enrich_company_deep(
        company_name="AcmeTech",
        domain="acmetech.com",
        careers_page_url="https://acmetech.com/careers",
        target_count=8,
        conn=mock_db,
    )

    assert res["new_leads_added"] >= 8
    assert res["total_leads"] >= 8

    # Verify leads in database
    db_leads = mock_db.execute("SELECT * FROM recruiter_leads WHERE company_name = 'AcmeTech'").fetchall()
    assert len(db_leads) >= 8

    alex_lead = [l for l in db_leads if "alex" in l["contact_email"]][0]
    assert alex_lead["contact_name"] == "Alex Mercer"
    assert alex_lead["execution_route"] == "DUAL_ATTACK"
    assert "AcmeTech" in alex_lead["linkedin_connection_note"]
