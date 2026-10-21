"""Unit tests for Tier 1 Semantic Q&A matching and label normalization."""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from applypilot.database import init_db, store_qa
from applypilot.learning.tier1_semantic_qa import (
    normalize_question,
    compute_question_hash,
    match_dropdown_option,
    resolve_screening_question,
)


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_qa.db"
    conn = init_db(db_file)
    return conn


def test_normalize_question_boilerplate_stripping():
    q1 = "* Please indicate your total years of work experience in software engineering:"
    assert normalize_question(q1) == "years_experience"

    q2 = "Are you legally authorized to work in the United States?"
    assert normalize_question(q2) == "work_authorization"

    q3 = "What is your desired salary / compensation expectation? (Annual in USD)"
    assert normalize_question(q3) == "desired_salary"

    q4 = "Will you now or in the future require visa sponsorship?"
    assert normalize_question(q4) == "work_authorization"

    q5 = "Are you willing to relocate for this position?"
    assert normalize_question(q5) == "willing_to_relocate"


def test_compute_question_hash():
    h1 = compute_question_hash("work_authorization")
    h2 = compute_question_hash("work_authorization")
    h3 = compute_question_hash("years_experience")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64


def test_match_dropdown_option_rapidfuzz():
    options = [
        "Bachelor's Degree",
        "Master's Degree (M.S. / M.A.)",
        "Doctorate (Ph.D.)",
        "High School Diploma / GED",
    ]

    # Fuzzy match variations
    assert match_dropdown_option("bachelors", options) == "Bachelor's Degree"
    assert match_dropdown_option("Master of Science", options) == "Master's Degree (M.S. / M.A.)"
    assert match_dropdown_option("PhD", options) == "Doctorate (Ph.D.)"


def test_match_dropdown_option_booleans():
    options_yes_no = ["Yes, authorized", "No, require sponsorship"]
    assert match_dropdown_option("Yes", options_yes_no) == "Yes, authorized"
    assert match_dropdown_option("No", options_yes_no) == "No, require sponsorship"

    simple_options = ["Yes", "No", "Decline to answer"]
    assert match_dropdown_option("true", simple_options) == "Yes"
    assert match_dropdown_option("false", simple_options) == "No"


def test_resolve_screening_question_from_profile(test_db):
    profile = {
        "work_authorization": "Yes, legally authorized without sponsorship",
        "notice_period": "2 weeks",
        "desired_salary": "$150,000",
        "willing_to_relocate": True,
        "years_of_experience": "6",
    }

    # Work auth dropdown
    val, conf, src = resolve_screening_question(
        "Do you have legal authorization to work in the US?",
        options=["Yes, authorized", "No sponsorship"],
        profile=profile,
        conn=test_db,
    )
    assert val == "Yes, authorized"
    assert conf == 1.0
    assert src == "profile"

    # Notice period text field
    val, conf, src = resolve_screening_question(
        "What is your notice period or availability?",
        profile=profile,
        conn=test_db,
    )
    assert val == "2 weeks"
    assert conf == 1.0
    assert src == "profile"


def test_resolve_screening_question_from_qa_knowledge(test_db):
    # Seed a Q&A pair in database
    store_qa(
        question="Describe your experience with Docker and Kubernetes",
        answer="Over 5 years deploying microservices using Helm charts and ArgoCD.",
        source="human_email",
        canonical_question="kubernetes_experience",
        conn=test_db,
    )

    val, conf, src = resolve_screening_question(
        "Describe your experience with Docker and Kubernetes",
        profile={},
        conn=test_db,
    )
    assert val == "Over 5 years deploying microservices using Helm charts and ArgoCD."
    assert conf >= 0.90
    assert src in {"qa_hash", "qa_exact"}


def test_unresolved_screening_question(test_db):
    val, conf, src = resolve_screening_question(
        "What is your favorite book about distributed systems?",
        profile={},
        conn=test_db,
    )
    assert val is None
    assert conf == 0.0
    assert src == "unresolved"
