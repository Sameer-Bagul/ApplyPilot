"""Unit tests for cdx_harvester (Common Crawl CDX, open-apply-jobs, JSON-LD Schema Extractor)."""

import json
from unittest.mock import MagicMock, patch
import pytest

from applypilot.career_resolver.cdx_harvester import (
    extract_jobpostings_from_html,
    extract_slug_from_ats_url,
    get_latest_common_crawl_index,
    harvest_common_crawl_slugs,
    harvest_crtsh_career_subdomains,
    harvest_sitemap_career_urls,
    bootstrap_from_open_apply_jobs,
    sync_slugs_to_watchlist,
)
from applypilot.database import init_db, get_career_watchlist


def test_extract_slug_from_ats_url():
    # Greenhouse
    assert extract_slug_from_ats_url("https://boards.greenhouse.io/stripe/jobs/123", "greenhouse") == "stripe"
    assert extract_slug_from_ats_url("https://boards.greenhouse.io/embed/job_board?for=openai", "greenhouse") == "openai"
    assert extract_slug_from_ats_url("https://boards.greenhouse.io/api/v1/jobs", "greenhouse") is None  # reserved

    # Lever
    assert extract_slug_from_ats_url("https://jobs.lever.co/figma/abc-def", "lever") == "figma"
    assert extract_slug_from_ats_url("https://jobs.lever.co/jobs", "lever") is None  # reserved

    # Ashby
    assert extract_slug_from_ats_url("https://jobs.ashbyhq.com/ramp", "ashby") == "ramp"
    assert extract_slug_from_ats_url("https://jobs.ashbyhq.com/100ms/18b264e0", "ashby") == "100ms"

    # Workable
    assert extract_slug_from_ats_url("https://apply.workable.com/aircall/j/123", "workable") == "aircall"

    # SmartRecruiters
    assert extract_slug_from_ats_url("https://careers.smartrecruiters.com/Visa/743999", "smartrecruiters") == "visa"

    # BambooHR
    assert extract_slug_from_ats_url("https://acme.bamboohr.com/careers/24", "bamboohr") == "acme"


def test_extract_jobpostings_from_html():
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Careers at Acme AI</title>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org/",
            "@type": "JobPosting",
            "title": "Senior AI Systems Engineer",
            "description": "<p>Build agentic AI runtime.</p>",
            "hiringOrganization": {
                "@type": "Organization",
                "name": "Acme AI Corp"
            },
            "jobLocation": {
                "@type": "Place",
                "address": {
                    "addressLocality": "San Francisco",
                    "addressRegion": "CA",
                    "addressCountry": "US"
                }
            },
            "employmentType": "FULL_TIME",
            "datePosted": "2026-11-01",
            "url": "https://acme.ai/careers/senior-ai-engineer",
            "baseSalary": {
                "@type": "MonetaryAmount",
                "currency": "USD",
                "value": {
                    "minValue": 180000,
                    "maxValue": 240000
                }
            }
        }
        </script>
    </head>
    <body>
        <h1>Work with us</h1>
    </body>
    </html>
    """

    jobs = extract_jobpostings_from_html(sample_html, base_url="https://acme.ai/careers")
    assert len(jobs) == 1
    j = jobs[0]
    assert j["title"] == "Senior AI Systems Engineer"
    assert j["company"] == "Acme AI Corp"
    assert j["location"] == "San Francisco, CA, US"
    assert j["salary_min"] == 180000
    assert j["salary_max"] == 240000
    assert j["salary_currency"] == "USD"
    assert j["url"] == "https://acme.ai/careers/senior-ai-engineer"
    assert j["ats_provider"] == "json_ld_schema"


def test_extract_jobpostings_graph_container():
    graph_html = """
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "name": "Databot"
            },
            {
                "@type": "JobPosting",
                "title": "Lead Python Engineer",
                "hiringOrganization": "Databot Inc",
                "url": "https://databot.io/jobs/lead-python"
            }
        ]
    }
    </script>
    """
    jobs = extract_jobpostings_from_html(graph_html)
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Lead Python Engineer"
    assert jobs[0]["company"] == "Databot Inc"
    assert jobs[0]["url"] == "https://databot.io/jobs/lead-python"


def test_harvest_sitemap_career_urls():
    sitemap_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url><loc>https://company.com/</loc></url>
        <url><loc>https://company.com/about</loc></url>
        <url><loc>https://company.com/blog/article-1</loc></url>
        <url><loc>https://company.com/careers/senior-backend-engineer</loc></url>
        <url><loc>https://company.com/jobs/ai-researcher</loc></url>
    </urlset>
    """
    mock_resp = MagicMock()
    mock_resp.read.return_value = sitemap_xml
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        urls = harvest_sitemap_career_urls("https://company.com/sitemap.xml")
        assert len(urls) == 2
        assert "https://company.com/careers/senior-backend-engineer" in urls
        assert "https://company.com/jobs/ai-researcher" in urls


def test_sync_slugs_to_watchlist(tmp_path):
    db_path = tmp_path / "test_watchlist.db"
    conn = init_db(db_path)

    entries = [
        {"company_name": "Datadog", "ats_provider": "greenhouse", "ats_board_token": "datadog"},
        {"company_name": "Ramp", "ats_provider": "ashby", "ats_board_token": "ramp"},
        {"company_name": "Figma", "ats_provider": "lever", "ats_board_token": "figma"},
    ]

    saved = sync_slugs_to_watchlist(entries, conn=conn)
    assert saved == 3

    watchlist = get_career_watchlist(conn=conn)
    names = [w["company_name"] for w in watchlist]
    assert "Datadog" in names
    assert "Ramp" in names
    assert "Figma" in names


def test_harvest_common_crawl_slugs_mocked():
    cdx_lines = "\n".join([
        json.dumps({"url": "https://boards.greenhouse.io/stripe/jobs/101"}),
        json.dumps({"url": "https://boards.greenhouse.io/stripe/jobs/102"}),
        json.dumps({"url": "https://boards.greenhouse.io/airbnb/jobs/201"}),
        json.dumps({"url": "https://boards.greenhouse.io/embed/job_board?for=openai"}),
        json.dumps({"url": "https://boards.greenhouse.io/api/v1/jobs"}),  # reserved
    ]).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.read.return_value = cdx_lines
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        slugs = harvest_common_crawl_slugs("greenhouse", limit=10, index_id="CC-MAIN-2026-43")
        assert "stripe" in slugs
        assert "airbnb" in slugs
        assert "openai" in slugs
        assert "api" not in slugs


def test_bootstrap_from_open_apply_jobs_mocked():
    mock_api_payload = json.dumps({
        "rows": [
            {
                "row": {
                    "title": "Senior AI Systems Engineer",
                    "source_slug": "anthropic",
                    "apply_url": "https://jobs.lever.co/anthropic/123",
                    "description_html": "Build Python and PyTorch models",
                    "locations": ["San Francisco, CA"],
                    "employment_type": "FullTime",
                }
            },
            {
                "row": {
                    "title": "Executive Assistant",
                    "source_slug": "acme",
                    "apply_url": "https://boards.greenhouse.io/acme/456",
                    "description_html": "Calendar management",
                    "locations": ["New York"],
                    "employment_type": "FullTime",
                }
            }
        ]
    }).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.read.return_value = mock_api_payload
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        # Filter for AI/Python
        jobs = bootstrap_from_open_apply_jobs(limit=10, target_keywords=["python", "ai"])
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Senior AI Systems Engineer"
        assert jobs[0]["company"] == "anthropic"
        assert jobs[0]["ats_provider"] == "lever"
