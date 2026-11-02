"""Unit tests for Phase 5: 5-Tier Zero-Token Learning, Canonical Matcher, and Trace Analyzer."""

import json
import sqlite3
import pytest
from applypilot.database import init_db, store_qa
from applypilot.learning.canonical_matcher import (
    execute_pattern_transform,
    lookup_canonical_answer,
    match_dropdown_option,
    normalize_field_label,
)
from applypilot.learning.tier0_replay import (
    compute_page_step_signature,
    get_cached_selectors_for_step,
)
from applypilot.learning.trace_analyzer import analyze_and_promote_traces


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_5tier.db"
    conn = init_db(db_file)
    return conn, db_file


def test_normalize_field_label():
    label = "  * 1. Please indicate your current notice period (in weeks)?  "
    norm = normalize_field_label(label)
    assert "notice_period" in norm
    assert "*" not in norm


def test_match_dropdown_option_rapidfuzz():
    options = [
        "Yes, I am legally authorized to work in the United States without sponsorship",
        "No, I will require sponsorship now or in the future",
        "Decline to state",
    ]
    matched, score = match_dropdown_option("Yes", options)
    assert matched == options[0]
    assert score >= 0.85

    matched_no, score_no = match_dropdown_option("No", options)
    assert matched_no == options[1]
    assert score_no >= 0.85


def test_execute_pattern_transform():
    # Phone number transform
    phone = execute_pattern_transform("mobile phone number", "4155552671")
    assert phone == "+14155552671"

    # Months of experience
    months = execute_pattern_transform("experience (months)", "3")
    assert months == "36"


def test_lookup_canonical_answer_profile_and_fts(test_db):
    conn, _ = test_db
    profile = {
        "name": "Alex Mercer",
        "email": "alex@example.com",
        "authorized_in_us": True,
    }

    # 1. Profile lookup
    ans, conf, src = lookup_canonical_answer("Email Address", profile=profile, conn=conn)
    assert ans == "alex@example.com"
    assert conf == 1.0

    # 2. Store fact in QA and test FTS lookup
    conn.execute(
        "INSERT INTO qa_fts (question_key, canonical_question, question_text, answer_text) "
        "VALUES ('kubernetes_experience', 'How many years with Kubernetes?', 'Experience with Kubernetes', '4+ years')"
    )
    conn.commit()

    ans_fts, conf_fts, src_fts = lookup_canonical_answer("Experience with Kubernetes in production", conn=conn)
    assert ans_fts == "4+ years"
    assert conf_fts >= 0.9
    assert src_fts == "qa_fts"


def test_compute_page_step_signature():
    sig1 = compute_page_step_signature(["input_first_name", "input_email", "input_resume"])
    sig2 = compute_page_step_signature(["input_email", "input_first_name", "input_resume"])
    assert sig1 == sig2
    assert len(sig1) == 16


def test_analyze_and_promote_traces(test_db, tmp_path):
    conn, _ = test_db
    trace_path = tmp_path / "apply_trace.jsonl"

    traces = [
        {
            "ats_type": "greenhouse",
            "url": "https://boards.greenhouse.io/test/jobs/1",
            "selector": "input#custom_field_123",
            "action_type": "fill",
            "target_key": "custom_field_123",
            "label": "Are you willing to work in hybrid model?",
            "value": "Yes, hybrid is great",
            "validation_passed": True,
        }
    ]
    with open(trace_path, "w", encoding="utf-8") as f:
        for t in traces:
            f.write(json.dumps(t) + "\n")

    summary = analyze_and_promote_traces(trace_log_path=trace_path, conn=conn)
    assert summary["promoted_selectors"] == 1
    assert summary["promoted_qa"] == 1
    assert summary["by_ats"].get("greenhouse") == 1
