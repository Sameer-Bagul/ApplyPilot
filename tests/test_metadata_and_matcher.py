"""Unit tests for Job Metadata Extractor and Resume-to-JD Matcher."""

import pytest

from applypilot.enrichment.metadata_extractor import (
    extract_workplace_type,
    extract_experience_requirements,
    extract_role_category,
    extract_tech_stack,
    extract_all_metadata,
)
from applypilot.scoring.resume_matcher import (
    evaluate_job_match,
    compute_skill_overlap_score,
    compute_experience_fit_score,
    compute_role_alignment_score,
)


def test_workplace_type_detection():
    assert extract_workplace_type("Remote - Worldwide", "Great opportunity") == "Remote"
    assert extract_workplace_type("Bengaluru", "This is a 100% remote role") == "Remote"
    assert extract_workplace_type("San Francisco", "Hybrid schedule: 2 days in office") == "Hybrid"
    assert extract_workplace_type("Pune, India", "Must work onsite at our Pune office") == "Onsite"


def test_experience_extraction():
    # Explicit years
    exp1 = extract_experience_requirements("Software Engineer", "Requires at least 3 years of experience in Python.")
    assert exp1["min_years"] == 3
    assert exp1["level"] == "Mid"

    # Range
    exp2 = extract_experience_requirements("Senior Backend Engineer", "Looking for someone with 5-8 years of experience.")
    assert exp2["min_years"] == 5
    assert exp2["max_years"] == 8
    assert exp2["level"] == "Senior"

    # Staff / High seniority
    exp3 = extract_experience_requirements("Staff Engineer", "Must have 10+ years of professional experience.")
    assert exp3["min_years"] == 10
    assert exp3["level"] == "Staff"

    # Intern
    exp4 = extract_experience_requirements("Software Engineering Intern", "Current college students.")
    assert exp4["level"] == "Intern"


def test_role_categorization():
    assert extract_role_category("AI Engineer")[0] == "AI_ML"
    assert extract_role_category("Senior Machine Learning Scientist")[0] == "AI_ML"
    assert extract_role_category("Full Stack Developer")[0] == "FULLSTACK"
    assert extract_role_category("Backend Engineer - Python")[0] == "BACKEND"
    assert extract_role_category("DevOps / Cloud Engineer")[0] == "DEVOPS_CLOUD"
    assert extract_role_category("Enterprise Account Executive")[0] == "NON_TECH"
    assert extract_role_category("Technical Recruiter")[0] == "NON_TECH"


def test_tech_stack_extraction():
    jd = """
    We are seeking a Python engineer experienced with FastAPI, React, and TypeScript.
    Knowledge of PostgreSQL, Redis, Docker, and Kubernetes is required.
    Familiarity with LangChain, LLMs, and PyTorch is a major plus.
    """
    stack = extract_tech_stack(jd)
    for expected in ["python", "fastapi", "react", "typescript", "postgresql", "redis", "docker", "kubernetes", "langchain", "llm", "pytorch"]:
        assert expected in stack


def test_resume_matching_high_fit():
    job = {
        "title": "AI / Full Stack Engineer",
        "location": "Remote",
        "description": "Building agentic AI tools with Python, FastAPI, React, TypeScript, Docker, and LangChain. 2-4 years experience.",
    }
    match = evaluate_job_match(job)
    assert match["match_percentage"] >= 80
    assert match["fit_score"] >= 8
    assert "🟢" in match["badge"]
    assert "python" in match["matched_skills"]
    assert "fastapi" in match["matched_skills"]


def test_resume_matching_non_tech_rejection():
    job = {
        "title": "Account Executive, Mid-Market",
        "location": "Remote",
        "description": "Drive quota for our SaaS platform.",
    }
    match = evaluate_job_match(job)
    assert match["match_percentage"] == 0
    assert match["fit_score"] == 1
    assert match["triage_action"] == "archive"


def test_resume_matching_staff_over_senior():
    job = {
        "title": "Principal Distributed Systems Architect",
        "location": "San Francisco, CA (Onsite)",
        "description": "Requires minimum 12+ years of experience designing high-scale infrastructure.",
    }
    match = evaluate_job_match(job)
    # Penalized for over-seniority (12+ yrs vs candidate's 2.5 yrs)
    assert match["match_percentage"] < 65
    assert "Staff/Principal" in match["experience_label"]
