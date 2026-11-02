"""Unit & integration test roundtrip for Phase 3 Email HITL."""

from __future__ import annotations

import argparse
import sys
import pytest
from applypilot.database import (
    get_connection,
    init_db,
    lookup_qa_by_hash,
    store_recruiter_lead,
)
from applypilot.hitl.email_notifier import park_and_notify_user
from applypilot.hitl.email_reply_parser import (
    parse_reply_answers,
    process_hitl_ticket_reply,
)
from applypilot.learning.tier1_semantic_qa import (
    compute_question_hash,
    normalize_question,
)


def run_test_roundtrip(mock: bool = True) -> bool:
    conn = init_db()

    # Step 1: Create a mock recruiter lead
    lead_id = store_recruiter_lead(
        contact_email="test.recruiter@example.com",
        role_title="Senior AI Engineer",
        company_name="ApexAI",
        execution_route="DUAL_ATTACK",
        conn=conn,
    )

    # Step 2: Trigger HITL notification for unknown questions
    unknown_questions = [
        {
            "id": "q_work_auth",
            "label": "Are you legally authorized to work in the United States?",
            "type": "select",
            "options": ["Yes", "No"],
        },
        {
            "id": "q_notice_period",
            "label": "What is your official notice period?",
            "type": "text",
            "options": [],
        },
    ]

    ticket_id = park_and_notify_user(
        lead_id=lead_id,
        company="ApexAI",
        role_title="Senior AI Engineer",
        job_url="https://apexai.example.com/careers/ai-engineer",
        blocker_type="unknown_screening_question",
        unknown_questions=unknown_questions,
        mock=mock,
        conn=conn,
    )

    # Step 3: Simulate user reply via email
    simulated_reply = """
    Hi ApplyPilot, here are my answers:
    A1: Yes
    A2: Immediate (available in 14 days)

    On Mon, Nov 2, 2026 at 4:00 PM ApplyPilot wrote:
    > Please reply to this email
    """
    answers = parse_reply_answers(simulated_reply)
    assert answers.get(1) == "Yes", f"Expected Yes, got {answers.get(1)}"
    assert "Immediate" in answers.get(2, ""), f"Expected Immediate, got {answers.get(2)}"

    # Step 4: Process ticket resolution
    res = process_hitl_ticket_reply(ticket_id, simulated_reply, conn=conn)
    assert res["success"] is True

    # Step 5: Verify QA knowledge base and FTS
    norm_q = normalize_question(unknown_questions[0]["label"])
    q_hash = compute_question_hash(norm_q)
    stored = lookup_qa_by_hash(q_hash, conn=conn)
    assert len(stored) > 0

    return True


def test_hitl_roundtrip_execution():
    """Pytest test case executing mock roundtrip."""
    assert run_test_roundtrip(mock=True) is True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test ApplyPilot HITL Roundtrip")
    parser.add_argument("--live", action="store_true", help="Send actual Gmail message")
    args = parser.parse_args()

    success = run_test_roundtrip(mock=not args.live)
    sys.exit(0 if success else 1)
