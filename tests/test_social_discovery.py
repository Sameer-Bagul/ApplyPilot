"""Unit tests for Phase 2: Social Discovery, Extractor, ATS Feeds, and Career Resolver."""

import pytest
from applypilot.social_discovery.extractor import (
    classify_contact_type,
    classify_execution_route,
    extract_ats_urls,
    extract_emails,
    extract_evidence_snippet,
    parse_social_post,
)
from applypilot.social_discovery.reddit_scraper import is_hiring_post
from applypilot.career_resolver.resolver import unshorten_url
from applypilot.social_discovery.orchestrator import run_omni_channel_discovery
from applypilot.database import init_db, get_recruiter_leads


def test_extract_emails_standard_and_obfuscated():
    text = """
    We are hiring a Senior Python Engineer at TechFlow!
    Please send your resume to alex@techflow.io or contact sarah [at] techflow [dot] io.
    Don't send to noreply@techflow.io or support@example.com.
    You can also reach out to jobs(at)techflow(dot)ai for any questions.
    """
    emails = extract_emails(text)
    assert "alex@techflow.io" in emails
    assert "sarah@techflow.io" in emails
    assert "jobs@techflow.ai" in emails
    assert "noreply@techflow.io" not in emails
    assert "support@example.com" not in emails


def test_extract_ats_urls():
    text = """
    Apply via Greenhouse: https://boards.greenhouse.io/stripe/jobs/123456
    Or Lever: https://jobs.lever.co/figma/abcdef
    Or visit our website: https://stripe.com
    """
    ats_links = extract_ats_urls(text)
    assert "https://boards.greenhouse.io/stripe/jobs/123456" in ats_links
    assert "https://jobs.lever.co/figma/abcdef" in ats_links
    assert "https://stripe.com" not in ats_links


def test_classify_execution_routes():
    assert classify_execution_route(has_email=True, has_portal_url=False) == "EMAIL_ONLY"
    assert classify_execution_route(has_email=False, has_portal_url=True) == "PORTAL_ONLY"
    assert classify_execution_route(has_email=True, has_portal_url=True) == "DUAL_ATTACK"
    assert classify_execution_route(has_email=False, has_portal_url=False) == "UNKNOWN"


def test_classify_contact_types():
    assert classify_contact_type("ceo@startup.io", "I am the founder & CEO") == "founder"
    assert classify_contact_type("jane@corp.com", "Hi, I am lead recruiter here") == "recruiter"
    assert classify_contact_type("engineering-manager@firm.com", "Hiring manager for core infra") == "hiring_manager"
    assert classify_contact_type("careers@acme.com", "") == "careers_inbox"


def test_parse_social_post_dual_attack():
    title = "[Hiring] FastStartup is hiring a Lead AI Engineer"
    text = """
    We are looking for an AI Engineer to join our team.
    Apply on our portal: https://jobs.ashbyhq.com/faststartup/123
    Or email the founder directly at founder@faststartup.ai with your GitHub profile!
    """
    res = parse_social_post(title, text, source_url="https://x.com/post/1", platform="x")
    assert res["execution_route"] == "DUAL_ATTACK"
    assert res["primary_email"] == "founder@faststartup.ai"
    assert res["contact_type"] == "founder"
    assert "https://jobs.ashbyhq.com/faststartup/123" in res["ats_urls"]
    assert "founder@faststartup.ai" in res["evidence_snippet"]


def test_reddit_is_hiring_post_filter():
    assert is_hiring_post({"title": "[Hiring] Fullstack React/Node Engineer $120k", "link_flair_text": "Hiring"}) is True
    assert is_hiring_post({"title": "[For Hire] Senior Developer available for hire", "link_flair_text": "For Hire"}) is False
    assert is_hiring_post({"title": "[ForHire] Python dev with 5 years experience", "link_flair_text": ""}) is False


def test_discovery_orchestrator_dry_run():
    # Calling orchestrator with mock or empty sources to verify structure
    summary = run_omni_channel_discovery(sources=[], dry_run=True)
    assert summary["dry_run"] is True
    assert "total_discovered" in summary
    assert "route_counts" in summary
