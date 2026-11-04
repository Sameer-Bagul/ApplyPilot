"""Unit tests for Free Multi-Tier Email Harvester and Fallback Engine."""

import pytest
from unittest.mock import patch, MagicMock

from applypilot.database import init_db
from applypilot.discovery.email_hunter import (
    clean_domain,
    check_domain_mx_provider,
    HunterClient,
    ZeroTokenOSINTFinder,
    harvest_company_emails_cascade,
)


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_email.db"
    conn = init_db(db_file)
    yield conn
    conn.close()


def test_clean_domain():
    assert clean_domain("https://www.stripe.com/careers/jobs") == "stripe.com"
    assert clean_domain("http://sub.domain.co.uk:8080/path?q=1") == "sub.domain.co.uk"
    assert clean_domain("www.gusto.com") == "gusto.com"
    assert clean_domain("razorpay.com") == "razorpay.com"
    assert clean_domain("") == ""


def test_zero_token_osint_with_mocked_dns():
    finder = ZeroTokenOSINTFinder()

    with patch("applypilot.discovery.email_hunter.check_domain_mx_provider") as mock_mx, \
         patch("applypilot.discovery.email_hunter.scrape_company_site_leadership") as mock_site:

        mock_mx.return_value = (True, "google_workspace")
        mock_site.return_value = {
            "emails": ["founders@acmecorp.com"],
            "executives": [{"name": "Jane Doe", "role": "Head of Talent"}],
        }

        res = finder.harvest_company_emails("acmecorp.com", company_name="Acme Corp", limit=5)

        assert res["domain"] == "acmecorp.com"
        assert res["mx_valid"] is True
        assert res["mx_provider"] == "google_workspace"
        assert res["total_found"] >= 2

        emails = [lead["email"] for lead in res["leads"]]
        assert "founders@acmecorp.com" in emails
        assert "careers@acmecorp.com" in emails


def test_hunter_client_no_key_graceful_handling():
    client = HunterClient(api_key="")
    assert client.is_configured is False
    res = client.search_domain_emails("stripe.com")
    assert "error" in res


def test_harvest_company_emails_cascade_free_fallback(test_db):
    # Ensure without any paid Hunter keys, cascade succeeds and stores to DB
    with patch("applypilot.discovery.email_hunter.check_domain_mx_provider") as mock_mx:
        mock_mx.return_value = (True, "google_workspace")

        res = harvest_company_emails_cascade(
            domain="mockcompany.io",
            company_name="Mock Company",
            limit=5,
            store_to_db=True,
            conn=test_db,
        )

        assert res["domain"] == "mockcompany.io"
        assert res["company"] == "Mock Company"
        assert res["primary_source"] == "zero_token_osint"
        assert res["total_emails_found"] >= 1
        assert res["leads_stored_to_db"] >= 1

        row = test_db.execute(
            "SELECT contact_email, company_name, execution_route FROM recruiter_leads WHERE company_domain = 'mockcompany.io'"
        ).fetchone()

        assert row is not None
        assert "@mockcompany.io" in row["contact_email"]
        assert row["execution_route"] == "EMAIL_ONLY"

