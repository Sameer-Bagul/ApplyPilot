"""Unit tests for Multi-Source Directory Harvesters.

Tests:
- YC Harvester (yc_harvester.py)
- TopStartups Harvester (topstartups_harvester.py)
- BLR Startup Arena Harvester (blr_arena_harvester.py)
- Multi-Directory Orchestrator (multi_directory_orchestrator.py)
"""

from __future__ import annotations

import sqlite3
import pytest
from bs4 import BeautifulSoup

from applypilot.database import init_db
from applypilot.discovery.yc_harvester import (
    extract_founders_from_text,
    is_indian_yc_startup,
    is_remote_yc_startup,
    normalize_yc_startup,
    ingest_yc_startups_to_db,
)
from applypilot.discovery.topstartups_harvester import (
    extract_ats_apply_url,
    extract_company_website,
    parse_topstartups_card,
    ingest_topstartups_to_db,
)
from applypilot.discovery.blr_arena_harvester import (
    parse_blr_arena_companies,
    resolve_blr_arena_domain,
    normalize_blr_arena_company,
    ingest_blr_arena_to_db,
)


@pytest.fixture
def test_db(tmp_path):
    from applypilot.learning.migrations import run_migrations
    db_file = tmp_path / "test.db"
    conn = init_db(db_file)
    run_migrations(db_file)
    yield conn
    conn.close()


# --- YC Harvester Tests ---

def test_yc_extract_founders_from_text():
    text = (
        "Razorpay was founded by Harshil Mathur (CEO & Co-Founder) and "
        "Shashank Kumar (MD & Co-Founder) to simplify payments in India."
    )
    founders = extract_founders_from_text(text)
    assert "Harshil Mathur" in founders
    assert "Shashank Kumar" in founders


def test_yc_location_filters():
    blr_company = {
        "all_locations": "Bengaluru, KA, India",
        "regions": ["India", "South Asia", "Remote"],
        "tags": ["Fintech", "India"],
    }
    us_company = {
        "all_locations": "San Francisco, CA, USA",
        "regions": ["United States"],
        "tags": ["AI"],
    }
    remote_company = {
        "all_locations": "Remote",
        "regions": ["Remote"],
        "tags": ["Developer Tools"],
    }

    assert is_indian_yc_startup(blr_company) is True
    assert is_indian_yc_startup(us_company) is False

    assert is_remote_yc_startup(blr_company) is True
    assert is_remote_yc_startup(remote_company) is True
    assert is_remote_yc_startup(us_company) is False


def test_yc_normalize_and_ingest(test_db):
    raw = {
        "id": 827,
        "name": "Razorpay",
        "slug": "razorpay",
        "website": "https://razorpay.com",
        "all_locations": "Bengaluru, KA, India",
        "long_description": "Founded by Harshil Mathur (CEO) and Shashank Kumar (CTO).",
        "batch": "Winter 2015",
        "stage": "Growth",
        "team_size": 2700,
        "tags": ["Fintech"],
    }
    normalized = normalize_yc_startup(raw)
    assert normalized["name"] == "Razorpay"
    assert normalized["domain"] == "razorpay.com"
    assert "Harshil Mathur" in normalized["founders"]

    stats = ingest_yc_startups_to_db([normalized], enrich_emails=False, conn=test_db)
    assert stats["startups_ingested"] == 1

    row = test_db.execute("SELECT * FROM career_watchlist WHERE company_name = 'Razorpay'").fetchone()
    assert row is not None
    assert row["is_vip"] == 1
    assert row["priority_tier"] == 1
    assert "Harshil Mathur" in row["founders_json"]


# --- TopStartups Harvester Tests ---

def test_topstartups_extract_ats_and_website():
    card_html = """
    <div class="infinite-item">
        <h3><a href="https://job-boards.greenhouse.io/ethoslife/jobs/8920651002">Senior Marketing Designer</a></h3>
        <div><a href="http://www.ethoslife.com/?utm_source=topstartups.io">Ethos Life</a></div>
        <div><a href="https://linkedin.com/company/ethoslife">LinkedIn</a></div>
        <div>Sequoia $100M Series D in 2021</div>
    </div>
    """
    soup = BeautifulSoup(card_html, "html.parser")
    ats_url = extract_ats_apply_url(soup)
    website = extract_company_website(soup)
    parsed = parse_topstartups_card(soup)

    assert ats_url == "https://job-boards.greenhouse.io/ethoslife/jobs/8920651002"
    assert website == "http://www.ethoslife.com"
    assert parsed is not None
    assert parsed["company_name"] == "Ethos Life"
    assert parsed["domain"] == "ethoslife.com"
    assert parsed["apply_url"] == ats_url


def test_topstartups_ingest_to_db(test_db):
    job_item = {
        "title": "Staff Platform Engineer",
        "company_name": "Ethos Life",
        "domain": "ethoslife.com",
        "website_url": "https://ethoslife.com",
        "apply_url": "https://job-boards.greenhouse.io/ethoslife/jobs/123",
        "linkedin_url": "https://linkedin.com/company/ethoslife",
        "raw_text": "Sequoia Series D Ethos Life",
        "funding_info": "Sequoia Series D",
        "source": "topstartups",
    }
    stats = ingest_topstartups_to_db([job_item], enrich_emails=False, conn=test_db)
    assert stats["companies_ingested"] == 1
    assert stats["jobs_stored"] == 1

    row = test_db.execute("SELECT * FROM jobs WHERE company = 'Ethos Life'").fetchone()
    assert row is not None
    assert row["title"] == "Staff Platform Engineer"
    assert row["url"] == "https://job-boards.greenhouse.io/ethoslife/jobs/123"


# --- BLR Startup Arena Tests ---

def test_blr_arena_rsc_parse():
    mock_rsc_html = (
        'self.__next_f.push([1,"{\\"companies\\":[{\\"slug\\":\\"cred\\",\\"name\\":\\"CRED\\",'
        '\\"latitude\\":12.97,\\"longitude\\":77.64,\\"locality\\":\\"Indiranagar\\",'
        '\\"address\\":\\"100 Feet Rd, Indiranagar, Bengaluru\\",\\"jobCount\\":25,'
        '\\"facets\\":{\\"families\\":{\\"sde_backend\\":5,\\"ml_ai_engineering\\":3}}}],\\"modes\\":{}}"]);'
    )
    companies = parse_blr_arena_companies(mock_rsc_html)
    assert len(companies) == 1
    assert companies[0]["slug"] == "cred"
    assert companies[0]["name"] == "CRED"
    assert companies[0]["locality"] == "Indiranagar"
    assert companies[0]["jobCount"] == 25


def test_blr_arena_normalize_and_ingest(test_db):
    raw_co = {
        "slug": "cred",
        "name": "CRED",
        "locality": "Indiranagar",
        "address": "Indiranagar 100ft road",
        "jobCount": 15,
        "facets": {"families": {"sde_backend": 4, "devops_sre_cloud": 2}},
    }
    domain = resolve_blr_arena_domain("CRED", "cred")
    assert domain == "cred.club"

    normalized = normalize_blr_arena_company(raw_co)
    assert normalized["domain"] == "cred.club"
    assert "Indiranagar" in normalized["notes"]

    stats = ingest_blr_arena_to_db([normalized], enrich_emails=False, conn=test_db)
    assert stats["startups_ingested"] == 1

    row = test_db.execute("SELECT * FROM career_watchlist WHERE company_name = 'CRED'").fetchone()
    assert row is not None
    assert row["official_domain"] == "cred.club"
    assert row["is_vip"] == 1
    assert row["area"] == "Indiranagar"
