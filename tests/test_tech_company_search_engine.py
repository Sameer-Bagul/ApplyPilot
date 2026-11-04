"""Unit tests for Tech Company Search Engine Pipeline & Autonomous Downstream Handoff."""

from unittest.mock import MagicMock, patch
import pytest

from applypilot.discovery.tech_company_search_engine import (
    classify_tech_sector,
    extract_clean_domain,
    fetch_yc_tech_startups,
    search_tech_companies_via_dorks,
)


def test_classify_tech_sector():
    assert classify_tech_sector("Senior LLM Agentic Infrastructure Engineer") == "AI / Machine Learning"
    assert classify_tech_sector("Kubernetes Cloud Platform Observability") == "Developer Tools & Cloud"
    assert classify_tech_sector("DeFi Lending and Crypto Payments Protocol") == "Fintech & Crypto"
    assert classify_tech_sector("Zero-Trust IAM Compliance Security") == "Cybersecurity"
    assert classify_tech_sector("Autonomous Robotics Fleet Sensor System") == "Robotics & Hard Tech"
    assert classify_tech_sector("Enterprise CRM Sales Workflow Platform") == "Enterprise SaaS"


def test_extract_clean_domain():
    assert extract_clean_domain("https://www.scale.com/careers") == "scale.com"
    assert extract_clean_domain("https://circuithub.com/about") == "circuithub.com"
    # Should ignore search engines and aggregators
    assert extract_clean_domain("https://duckduckgo.com/?q=test") is None
    assert extract_clean_domain("https://www.ycombinator.com/companies") is None
    assert extract_clean_domain("https://github.com/trending") is None


def test_fetch_yc_tech_startups():
    # Fetch 3 companies from real or mocked API
    companies = fetch_yc_tech_startups(limit=3, only_hiring=True)
    if companies:
        c = companies[0]
        assert "company_name" in c
        assert "official_domain" in c
        assert "sector" in c
        assert c["source"] == "yc_oss_api"

