"""Unit tests for DeepWebSearcher."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from applypilot.discovery.deep_web_searcher import (
    DeepWebSearcher,
    is_valid_article_url,
)


def test_is_valid_article_url():
    assert is_valid_article_url("https://techcrunch.com/2026/01/15/clinikally-funding/") is True
    assert is_valid_article_url("https://www.linkedin.com/in/some-user") is False
    assert is_valid_article_url("https://twitter.com/startup") is False
    assert is_valid_article_url("https://example.com/pitchdeck.pdf") is False
    assert is_valid_article_url("") is False


def test_fetch_and_parse_article_mocked():
    searcher = DeepWebSearcher()

    sample_html = """
    <html>
        <body>
            <h1>Clinikally Scales Telehealth</h1>
            <p>Clinikally raised $15M in Series A funding to expand its engineering team.</p>
            <p>"We are democratizing healthcare," said Arjun Soin, Founder and CEO of Clinikally.</p>
            <p>For press inquiries, contact arjun.soin@clinikally.com or press@clinikally.com.</p>
        </body>
    </html>
    """

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = sample_html

    with patch("httpx.Client.get", return_value=mock_resp):
        res = searcher._fetch_and_parse_article(
            url="https://techcrunch.com/article",
            company_name="Clinikally",
            company_domain="clinikally.com",
        )

    assert len(res["emails"]) >= 1
    assert "arjun.soin@clinikally.com" in res["emails"]
    assert len(res["leaders"]) >= 1
    assert res["leaders"][0]["name"] == "Arjun Soin"
    assert len(res["milestones"]) >= 1
    assert "Series A" in res["milestones"][0]


def test_search_and_analyze_company_mocked():
    searcher = DeepWebSearcher()

    with patch.object(searcher, "_fetch_search_hits") as mock_hits, \
         patch.object(searcher, "_fetch_and_parse_article") as mock_article:

        mock_hits.return_value = [
            {"url": "https://techcrunch.com/test-article", "title": "Test", "body": "Snippet"},
            {"url": "https://linkedin.com/in/skip-me", "title": "Profile", "body": "Skip"},
        ]
        mock_article.return_value = {
            "emails": ["arjun.soin@clinikally.com"],
            "leaders": [{"name": "Arjun Soin", "role": "Executive / Leadership", "quote": "Quote", "source_url": "url"}],
            "milestones": ["Raised $10M"],
        }

        result = searcher.search_and_analyze_company("Clinikally", domain="clinikally.com")

        assert result["articles_checked"] == 1
        assert "arjun.soin@clinikally.com" in result["discovered_emails"]
        assert len(result["discovered_leaders"]) == 1
        assert result["discovered_leaders"][0]["name"] == "Arjun Soin"

