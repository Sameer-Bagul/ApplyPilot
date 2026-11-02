"""Interactive or automated test roundtrip for Phase 3 Email HITL.

Can be run via:
  uv run python -m applypilot.hitl.test_roundtrip
"""

from __future__ import annotations

import argparse
import sys
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
    print("=== Testing ApplyPilot Asynchronous Email HITL Roundtrip ===")
    conn = init_db()

    # Step 1: Create a mock recruiter lead
    lead_id = store_recruiter_lead(
        contact_email="test.recruiter@example.com",
        role_title="Senior AI Engineer",
        company_name="ApexAI",
        execution_route="DUAL_ATTACK",
        conn=conn,
    )
    print(f"1. Created test recruiter lead: {lead_id}")

    # Step 2: Park and notify user
    unknown_questions = [
        {
            "field_id": "q1",
            "label": "Do you have experience leading autonomous AI agent projects in production?",
            "field_type": "select",
            "required": True,
            "options": ["Yes, 3+ years", "Yes, 1-2 years", "No, personal projects only"],
        },
        {
            "field_id": "q2",
            "label": "What is your target notice period?",
            "field_type": "text",
            "required": True,
            "suggested_draft": "Immediate / 2 weeks",
        },
    ]

    ticket_id = park_and_notify_user(
        lead_id=lead_id,
        company="ApexAI",
        role_title="Senior AI Engineer",
        unknown_questions=unknown_questions,
        conn=conn,
    )
    print(f"2. Dispatched HITL notification ticket #{ticket_id}")

    # Step 3: Simulate email reply with A1 and A2
    simulated_reply = """
    Hi ApplyPilot, here are my answers:
    A1: A
    A2: Immediate (available in 14 days)

    On Mon, Nov 2, 2026 at 4:00 PM ApplyPilot wrote:
    > Please reply to this email
    """
    answers = parse_reply_answers(simulated_reply)
    print(f"3. Parsed answers from simulated reply: {answers}")
    assert answers.get(1) == "A", f"Expected A, got {answers.get(1)}"
    assert "Immediate" in answers.get(2, ""), f"Expected Immediate, got {answers.get(2)}"

    # Step 4: Process ticket resolution
    res = process_hitl_ticket_reply(ticket_id, simulated_reply, conn=conn)
    print(f"4. Ticket processing result: {res['success']}")
    assert res["success"] is True

    # Step 5: Verify QA knowledge base and FTS
    norm_q = normalize_question(unknown_questions[0]["label"])
    q_hash = compute_question_hash(norm_q)
    stored = lookup_qa_by_hash(q_hash, conn=conn)
    print(f"5. Stored Q&A answer verified in database: {stored[0]['answer_text'] if stored else 'None'}")
    assert len(stored) > 0

    print("=== HITL Roundtrip Test PASSED! ===")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test ApplyPilot HITL Roundtrip")
    parser.add_argument("--live", action="store_true", help="Send actual Gmail message")
    args = parser.parse_args()

    success = run_test_roundtrip(mock=not args.live)
    sys.exit(0 if success else 1)
