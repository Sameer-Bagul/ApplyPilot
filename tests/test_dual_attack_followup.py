"""Unit tests for the Coordinated Dual-Attack and 3-Day Follow-Up Generator."""

from applypilot.outreach.batch_draft_generator import _generate_fallback_draft


def test_fallback_draft_generates_followup():
    lead = {
        "lead_id": "test_lead_01",
        "company_name": "Acme AI",
        "contact_name": "Jane Doe",
        "contact_email": "jane@acme.ai",
        "role_title": "Founding Engineer",
        "persona": "founder",
        "company_intel": {
            "tech_stack": ["Python", "FastAPI", "LangGraph"],
            "open_roles": [{"title": "Founding Engineer", "url": "https://jobs.acme.ai/founding"}],
        },
        "execution_route": "DUAL_ATTACK",
        "dual_attack_pair_id": "dual_12345",
    }
    candidate = {
        "name": "Sameer Bagul",
        "email": "sameerbagul2004@gmail.com",
        "notice_period": "Immediate",
        "urls": {"github": "https://github.com/Sameer-Bagul"},
    }

    draft = _generate_fallback_draft(lead, candidate)
    assert draft["lead_id"] == "test_lead_01"
    assert "Sameer Bagul" in draft["subject"]
    assert "Athena" in draft["body_text"]  # Stack-aware matched project
    assert "submitted my formal profile" in draft["body_text"]  # Dual-attack bridge
    assert draft["followup_subject"].startswith("Re: ")
    assert "Following up quickly" in draft["followup_body"]


def test_fallback_draft_hr_job_citation():
    lead = {
        "lead_id": "test_lead_02",
        "company_name": "Acme AI",
        "contact_name": "Hiring Team",
        "contact_email": "hr@acme.ai",
        "role_title": "Full Stack Engineer",
        "matched_job_title": "Full Stack Engineer",
        "matched_job_url": "https://jobs.ashbyhq.com/acme/123",
        "persona": "hr",
        "company_intel": {
            "tech_stack": ["React", "TypeScript", "Next.js"],
        },
    }
    candidate = {
        "name": "Sameer Bagul",
        "email": "sameerbagul2004@gmail.com",
        "notice_period": "Immediate",
        "urls": {"github": "https://github.com/Sameer-Bagul"},
    }

    draft = _generate_fallback_draft(lead, candidate)
    assert "Full Stack Engineer" in draft["subject"]
    assert "https://jobs.ashbyhq.com/acme/123" in draft["body_text"]
    assert draft["followup_subject"].startswith("Re: ")

