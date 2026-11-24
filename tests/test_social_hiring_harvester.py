"""Unit tests for SocialHiringHarvester."""

from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock, patch
import pytest

from applypilot.database import init_db
from applypilot.discovery.social_hiring_harvester import (
    SocialHiringHarvester,
    parse_social_post_hit,
)


@pytest.fixture
def test_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def test_parse_social_post_hit():
    hit = {
        "url": "https://www.linkedin.com/posts/arjun-soin_hiring-startup-activity-12345",
        "title": 'Arjun Soin on LinkedIn: "We are hiring founding engineers at Clinikally"',
        "body": "We are looking for a Senior AI & Python engineer to join our team. Send resume or email me directly at arjun@clinikally.com!",
    }

    parsed = parse_social_post_hit(hit, "Clinikally", "linkedin_post")
    assert parsed is not None
    assert parsed["author_name"] == "Arjun Soin"
    assert parsed["platform"] == "linkedin_post"
    assert "arjun@clinikally.com" in parsed["embedded_emails"]
    assert "Found on Linkedin Post" in parsed["evidence_snippet"]
    assert parsed["post_url"] == hit["url"]


def test_harvest_company_hiring_posts_mocked(test_db):
    harvester = SocialHiringHarvester(conn=test_db)

    mock_hits = [
        {
            "href": "https://www.linkedin.com/posts/arjun-soin_hiring-123",
            "title": 'Arjun Soin on LinkedIn: "We\'re hiring!"',
            "body": "Looking for React & FastAPI developers. Reach out to arjun@clinikally.com.",
        }
    ]

    with patch("applypilot.discovery.social_hiring_harvester.DDGS") as mock_ddgs:
        instance = MagicMock()
        instance.text.return_value = mock_hits
        instance.__enter__.return_value = instance
        mock_ddgs.return_value = instance

        posts = harvester.harvest_company_hiring_posts("Clinikally", domain="clinikally.com")

        assert len(posts) >= 1
        assert posts[0]["author_name"] == "Arjun Soin"
        assert "arjun@clinikally.com" in posts[0]["embedded_emails"]

        # Test persistence
        added = harvester.persist_posts_to_leads(posts, "Clinikally", "clinikally.com", conn=test_db)
        assert added >= 1

        rows = test_db.execute(
            "SELECT * FROM recruiter_leads WHERE LOWER(company_name) = 'clinikally'"
        ).fetchall()
        assert len(rows) >= 1
        assert rows[0]["contact_name"] == "Arjun Soin"
        assert rows[0]["contact_email"] == "arjun@clinikally.com"
        assert rows[0]["execution_route"] == "DUAL_ATTACK"

