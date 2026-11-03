"""Tests for VC Portfolio Harvester, StartupFundraising, StartupMap.one, 11-ATS feeds, and Deep Company Looper."""

import json
import sqlite3
import pytest
from unittest.mock import MagicMock, patch

from applypilot.database import init_db
from applypilot.learning.migrations import run_migrations
from applypilot.discovery.vc_portfolio_harvester import (
    _normalize_getro_hits,
    parse_getro_next_data,
    ingest_vc_jobs_to_db,
)
from applypilot.discovery.startupfundraising_harvester import (
    parse_founders_html,
    ingest_fundraising_founders_to_db,
)
from applypilot.discovery.startupmap_one_harvester import (
    parse_startupmap_jobs,
    ingest_startupmap_jobs_to_db,
)
from applypilot.career_resolver.ats_feeds import (
    poll_board,
    poll_greenhouse_board,
    poll_lever_board,
    poll_ashby_board,
    poll_workable_board,
    poll_bamboohr_board,
    poll_smartrecruiters_board,
    poll_recruitee_board,
    poll_teamtailor_board,
    poll_breezy_board,
    poll_personio_board,
)
from applypilot.career_resolver.jsonld_parser import (
    compute_content_hash,
    extract_jsonld_jobpostings,
)
from applypilot.discovery.company_deep_looper import (
    loop_and_enrich_single_company,
    loop_all_watchlist_companies,
)


@pytest.fixture
def mem_db():
    conn = init_db(db_path=":memory:")
    run_migrations(db_path=conn)
    yield conn
    conn.close()


def test_normalize_getro_hits():
    hits = [
        {
            "title": "Staff Backend Engineer",
            "thirdPartyUrl": "https://boards.greenhouse.io/acko/jobs/12345",
            "company": {
                "name": "Acko",
                "domain": "acko.com",
                "stage": "Series D",
            },
            "locations": [{"name": "Bengaluru, India"}],
        },
        {
            "name": "Fullstack AI Engineer",
            "url": "https://jobs.lever.co/100ms/67890",
            "company": "100ms",
            "location": "Remote",
        },
    ]
    res = _normalize_getro_hits(hits)
    assert len(res) == 2
    assert res[0]["title"] == "Staff Backend Engineer"
    assert res[0]["company_name"] == "Acko"
    assert res[0]["company_domain"] == "acko.com"
    assert res[0]["ats_url"] == "https://boards.greenhouse.io/acko/jobs/12345"
    assert res[0]["location"] == "Bengaluru, India"
    assert res[1]["company_name"] == "100ms"


def test_parse_getro_next_data():
    sample_html = """
    <html>
      <head>
        <script id="__NEXT_DATA__" type="application/json">
          {
            "props": {
              "pageProps": {
                "jobs": [
                  {
                    "title": "Lead Software Engineer",
                    "thirdPartyUrl": "https://jobs.ashbyhq.com/accacia/999",
                    "company": {"name": "Accacia", "domain": "accacia.com"}
                  }
                ]
              }
            }
          }
        </script>
      </head>
      <body></body>
    </html>
    """
    jobs = parse_getro_next_data(sample_html)
    assert len(jobs) == 1
    assert jobs[0]["company_name"] == "Accacia"
    assert "ashbyhq.com" in jobs[0]["ats_url"]


def test_ingest_vc_jobs_to_db(mem_db):
    jobs_data = [
        {
            "title": "Senior AI Engineer",
            "company_name": "KhoslaAI",
            "company_domain": "khosla-ai.example",
            "ats_url": "https://boards.greenhouse.io/khoslaai/jobs/1",
            "stage": "Series A",
            "location": "Bengaluru",
        }
    ]
    with patch("applypilot.discovery.vc_portfolio_harvester.enrich_startup_emails_deep") as mock_enrich:
        mock_enrich.return_value = [
            {"email": "careers@khosla-ai.example", "type": "recruitment_inbox", "confidence": 0.9},
            {"email": "founder@khosla-ai.example", "type": "founder_direct", "confidence": 0.95},
        ]
        stats = ingest_vc_jobs_to_db(
            jobs_data=jobs_data,
            vc_source="Khosla Portfolio",
            enrich_emails=True,
            conn=mem_db,
        )

    assert stats["companies_ingested"] == 1
    assert stats["jobs_stored"] == 1
    assert stats["leads_created"] == 2

    co = mem_db.execute("SELECT * FROM career_watchlist WHERE company_name = 'KhoslaAI'").fetchone()
    assert co is not None
    assert co["is_vip"] == 1
    assert co["ats_provider"] == "greenhouse"

    job = mem_db.execute("SELECT * FROM jobs WHERE company = 'KhoslaAI'").fetchone()
    assert job["execution_route"] == "DUAL_ATTACK"


def test_parse_founders_html():
    sample_html = """
    <div>
      <a href="https://www.linkedin.com/in/tarun-mehta-ather" class="founder-link">Tarun Mehta</a>
      <span>Co-Founder at Ather Energy ($128M Series E)</span>
    </div>
    """
    founders = parse_founders_html(sample_html)
    assert len(founders) == 1
    assert founders[0]["founder_name"] == "Tarun Mehta"
    assert "linkedin.com/in/tarun-mehta-ather" in founders[0]["linkedin_url"]


def test_ingest_fundraising_founders_to_db(mem_db):
    founders = [
        {
            "founder_name": "Nithin Kamath",
            "company_name": "Zerodha",
            "linkedin_url": "https://www.linkedin.com/in/nithin-kamath",
            "funding": "Bootstrapped / Profitable",
            "source_url": "https://startupfundraising.com",
        }
    ]
    stats = ingest_fundraising_founders_to_db(founders, conn=mem_db)
    assert stats["founders_ingested"] == 1
    assert stats["companies_ingested"] == 1
    assert stats["notes_generated"] == 1

    lead = mem_db.execute("SELECT * FROM recruiter_leads WHERE company_name = 'Zerodha'").fetchone()
    assert lead is not None
    assert lead["contact_linkedin_url"] == "https://www.linkedin.com/in/nithin-kamath"
    assert len(lead["linkedin_connection_note"]) <= 280


def test_parse_startupmap_jobs():
    sample_html = """
    <html>
      <head>
        <script type="application/ld+json">
          {
            "@type": "JobPosting",
            "title": "Backend Python Developer",
            "hiringOrganization": {"name": "Sarvam AI"},
            "url": "https://boards.greenhouse.io/sarvamai/jobs/101",
            "jobLocation": {"address": {"addressLocality": "Bengaluru"}}
          }
        </script>
      </head>
      <body></body>
    </html>
    """
    jobs = parse_startupmap_jobs(sample_html)
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Backend Python Developer"
    assert jobs[0]["company_name"] == "Sarvam AI"
    assert "greenhouse.io" in jobs[0]["ats_url"]


def test_11_ats_board_pollers():
    # 1. Greenhouse
    with patch("httpx.Client.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"jobs": [{"title": "Eng", "absolute_url": "https://gh.io/1", "location": {"name": "BLR"}}]},
        )
        res = poll_greenhouse_board("testco")
        assert len(res) == 1
        assert res[0]["ats_provider"] == "greenhouse"

    # 2. Lever
    with patch("httpx.Client.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: [{"text": "Designer", "hostedUrl": "https://lever.co/2", "categories": {"location": "Remote"}}],
        )
        res = poll_lever_board("testco")
        assert len(res) == 1
        assert res[0]["ats_provider"] == "lever"

    # 3. Ashby
    with patch("httpx.Client.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"jobs": [{"title": "Data Eng", "jobUrl": "https://ashby.io/3", "location": "India"}]},
        )
        res = poll_ashby_board("testco")
        assert len(res) == 1
        assert res[0]["ats_provider"] == "ashby"

    # 4. Workable
    with patch("httpx.Client.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"jobs": [{"title": "ML Eng", "url": "https://workable.com/4", "city": "Bengaluru"}]},
        )
        res = poll_workable_board("testco")
        assert len(res) == 1
        assert res[0]["ats_provider"] == "workable"

    # 5. SmartRecruiters
    with patch("httpx.Client.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"content": [{"name": "DevOps", "id": "555", "location": {"city": "Remote"}}]},
        )
        res = poll_smartrecruiters_board("testco")
        assert len(res) == 1
        assert res[0]["ats_provider"] == "smartrecruiters"

    # 6. BambooHR
    with patch("httpx.Client.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"result": [{"jobOpeningName": "Frontend Lead", "id": "777", "location": {"city": "Pune"}}]},
        )
        res = poll_bamboohr_board("testco")
        assert len(res) == 1
        assert res[0]["ats_provider"] == "bamboohr"

    # 7. Recruitee
    with patch("httpx.Client.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"offers": [{"title": "QA Architect", "careers_url": "https://recruitee.com/8", "city": "Delhi"}]},
        )
        res = poll_recruitee_board("testco")
        assert len(res) == 1
        assert res[0]["ats_provider"] == "recruitee"

    # 8. Teamtailor
    with patch("httpx.Client.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: [{"attributes": {"title": "Fullstack", "url": "https://teamtailor.com/9", "location": "Remote"}}],
        )
        res = poll_teamtailor_board("testco")
        assert len(res) == 1
        assert res[0]["ats_provider"] == "teamtailor"

    # 9. Breezy
    with patch("httpx.Client.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: [{"name": "iOS Eng", "url": "https://breezy.hr/10", "location": {"name": "Remote"}}],
        )
        res = poll_breezy_board("testco")
        assert len(res) == 1
        assert res[0]["ats_provider"] == "breezy"

    # 10. Personio (XML)
    xml_content = b"""<workplace><position><id>123</id><name>Cloud Architect</name><office>Bengaluru</office></position></workplace>"""
    with patch("httpx.Client.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            content=xml_content,
        )
        res = poll_personio_board("testco")
        assert len(res) == 1
        assert res[0]["title"] == "Cloud Architect"
        assert res[0]["ats_provider"] == "personio"

    # Master poll_board dispatcher test
    with patch("applypilot.discovery.ats_direct_feeds.poll_greenhouse_board") as mock_gh:
        mock_gh.return_value = [{"title": "Dispatched GH"}]
        assert poll_board("greenhouse", "acme") == [{"title": "Dispatched GH"}]


def test_jsonld_parser():
    sample_html = """
    <html>
      <head>
        <script type="application/ld+json">
          {
            "@type": "JobPosting",
            "title": "Principal AI Scientist",
            "hiringOrganization": {"name": "Krish AI"},
            "url": "https://krish.ai/careers/principal-ai",
            "jobLocation": {
              "address": {
                "addressLocality": "Bengaluru",
                "addressCountry": "India"
              }
            }
          }
        </script>
      </head>
      <body><h1>Careers at Krish AI</h1></body>
    </html>
    """
    hash1 = compute_content_hash(sample_html)
    assert len(hash1) == 64  # SHA-256

    jobs = extract_jsonld_jobpostings(sample_html, base_url="https://krish.ai")
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Principal AI Scientist"
    assert jobs[0]["company"] == "Krish AI"
    assert jobs[0]["location"] == "Bengaluru, India"


def test_company_deep_looper_single_and_all(mem_db):
    # Insert a test company in career_watchlist
    mem_db.execute(
        """
        INSERT INTO career_watchlist (
            company_id, company_name, official_domain, careers_page_url,
            priority_tier, is_vip, ats_provider, ats_board_token,
            founders_json
        ) VALUES (
            'comp_test_1', 'SuperTech', 'supertech.io', 'https://boards.greenhouse.io/supertech',
            1, 1, 'greenhouse', 'supertech',
            '{"names": ["Saurabh Gupta"], "linkedin_urls": ["https://linkedin.com/in/saurabh-gupta"]}'
        )
        """
    )
    mem_db.commit()

    company = dict(mem_db.execute("SELECT * FROM career_watchlist WHERE company_name = 'SuperTech'").fetchone())

    def mock_deep_enrich(company_name, domain, careers_page_url=None, target_count=8, conn=None):
        from applypilot.database import store_recruiter_lead
        for em in ["saurabh@supertech.io", "careers@supertech.io", "talent@supertech.io"]:
            store_recruiter_lead(
                contact_email=em,
                role_title=f"Talent at {company_name}",
                company_name=company_name,
                company_domain=domain,
                source_platform="test",
                execution_route="DUAL_ATTACK",
                conn=conn,
            )
        return {
            "company": company_name,
            "domain": domain,
            "new_leads_added": 3,
            "total_leads": 3,
        }

    with patch("applypilot.discovery.company_deep_looper.enrich_company_deep", side_effect=mock_deep_enrich), \
         patch("applypilot.discovery.company_deep_looper.poll_board") as mock_poll:

        mock_poll.return_value = [
            {
                "title": "Senior Rust Engineer",
                "url": "https://boards.greenhouse.io/supertech/jobs/42",
                "location": "Bengaluru",
            }
        ]

        # Single company loop
        res = loop_and_enrich_single_company(
            company=company,
            enrich_emails=True,
            poll_jobs=True,
            conn=mem_db,
        )

        assert res["emails_added"] == 3
        assert res["new_jobs_found"] == 1
        assert res["total_jobs"] == 1

        # Check leads stored
        leads = mem_db.execute("SELECT * FROM recruiter_leads WHERE company_name = 'SuperTech'").fetchall()
        assert len(leads) == 3

        # Check job stored and assigned DUAL_ATTACK
        job = mem_db.execute("SELECT * FROM jobs WHERE company = 'SuperTech'").fetchone()
        assert job is not None
        assert job["title"] == "Senior Rust Engineer"
        assert job["execution_route"] == "DUAL_ATTACK"

        # Check loop_all_watchlist_companies
        summary = loop_all_watchlist_companies(priority_tier=1, conn=mem_db)
        assert summary["companies_processed"] == 1
