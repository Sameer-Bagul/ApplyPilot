"""Unit tests for the upgraded database schema, new tables, and state transitions.

Covers:
- Idempotent schema initialization and table existence:
  ats_selector_cache, hitl_tickets, ats_session_vault, pattern_rules, qa_knowledge
- QA knowledge extensions (canonical_question, question_hash, option_synonyms, category, embedding_blob)
- New pipeline state transitions: parked_awaiting_email, queued_resume
- Selector cache CRUD, ranking, and self-healing failure counting
- HITL ticket creation, dom_checkpoint serialization, and resolution
- ATS session vault caching and invalidation
- Pattern rules storage and hit-counting
- Concurrent WAL read/write integrity
"""

import json
import sqlite3
import sys
import threading
import tempfile
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from applypilot.database import (
    init_db,
    ensure_columns,
    ensure_qa_columns,
    VALID_STATES,
    VALID_TRANSITIONS,
    transition_state,
    current_state,
    store_qa,
    lookup_qa_by_hash,
    store_selector,
    get_selectors_for_domain,
    record_selector_result,
    create_hitl_ticket,
    get_hitl_ticket,
    get_pending_hitl_tickets,
    resolve_hitl_ticket,
    save_session_vault,
    get_session_vault,
    clear_session_vault,
    store_pattern_rule,
    get_pattern_rules,
    increment_pattern_rule_hit,
)


@pytest.fixture
def fresh_db(tmp_path):
    """Create a temporary database with full schema initialized."""
    db_file = tmp_path / "test_applypilot.db"
    conn = init_db(db_file)
    return conn, db_file


def test_new_tables_exist(fresh_db):
    conn, _ = fresh_db
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "ats_selector_cache" in tables
    assert "hitl_tickets" in tables
    assert "ats_session_vault" in tables
    assert "pattern_rules" in tables
    assert "qa_knowledge" in tables
    assert "job_state_transitions" in tables


def test_qa_knowledge_extended_columns(fresh_db):
    conn, _ = fresh_db
    columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(qa_knowledge)").fetchall()
    }
    expected = {
        "canonical_question",
        "question_hash",
        "embedding_blob",
        "source",
        "option_synonyms",
        "category",
        "use_count",
    }
    assert expected.issubset(columns)


def test_ensure_qa_columns_idempotent(fresh_db):
    conn, _ = fresh_db
    # Second call should add zero columns
    second_run = ensure_qa_columns(conn)
    assert second_run == []


def test_new_state_machine_transitions(fresh_db):
    conn, _ = fresh_db
    url = "https://example.com/jobs/senior-python-dev"

    # Insert a dummy job
    conn.execute(
        "INSERT INTO jobs (url, title, state) VALUES (?, ?, 'discovered')",
        (url, "Senior Python Developer"),
    )
    conn.commit()

    # Move through valid lifecycle to applying
    assert transition_state(conn, url, "enriched") is True
    assert transition_state(conn, url, "scored") is True
    assert transition_state(conn, url, "tailored") is True
    assert transition_state(conn, url, "ready_to_apply") is True
    assert transition_state(conn, url, "applying") is True

    # Unknown question encountered -> park awaiting email
    assert transition_state(conn, url, "parked_awaiting_email", reason="Missing 2 questions") is True
    assert current_state(conn, url) == "parked_awaiting_email"

    # Direct jump to applied while parked should fail
    assert transition_state(conn, url, "applied") is False
    assert current_state(conn, url) == "parked_awaiting_email"

    # Email reply received -> queued_resume
    assert transition_state(conn, url, "queued_resume", reason="Email reply parsed") is True
    assert current_state(conn, url) == "queued_resume"

    # Re-hydrated worker picks up -> applying -> applied
    assert transition_state(conn, url, "applying") is True
    assert transition_state(conn, url, "applied", reason="Submitted successfully") is True
    assert current_state(conn, url) == "applied"


def test_selector_cache_crud_and_ranking(fresh_db):
    conn, _ = fresh_db
    s1 = store_selector(
        ats_type="greenhouse",
        domain_pattern="job-boards.greenhouse.io",
        css_or_aria_selector="input#first_name",
        action_type="fill",
        target_key="profile.first_name",
        conn=conn,
    )
    assert s1 > 0

    # Record some successes
    record_selector_result(s1, success=True, conn=conn)
    record_selector_result(s1, success=True, conn=conn)

    s2 = store_selector(
        ats_type="greenhouse",
        domain_pattern="job-boards.greenhouse.io",
        css_or_aria_selector="input[name='first_name_alt']",
        action_type="fill",
        target_key="profile.first_name",
        conn=conn,
    )
    # Record a failure on s2
    record_selector_result(s2, success=False, conn=conn)

    selectors = get_selectors_for_domain("greenhouse", "job-boards.greenhouse.io", conn=conn)
    assert len(selectors) == 2
    # s1 has net +2 score, s2 has net -1, so s1 must come first
    assert selectors[0]["selector_id"] == s1
    assert selectors[0]["success_count"] == 2
    assert selectors[1]["selector_id"] == s2
    assert selectors[1]["failure_count"] == 1


def test_hitl_tickets_lifecycle(fresh_db):
    conn, _ = fresh_db
    url = "https://example.com/job/workday/1"
    conn.execute("INSERT INTO jobs (url, title) VALUES (?, ?)", (url, "ML Engineer"))
    conn.commit()

    questions = [
        {"id": "q1", "label": "Security Clearance", "type": "select", "options": ["Yes", "No"]},
        {"id": "q2", "label": "Years in Kubernetes", "type": "number"},
    ]
    dom_checkpoint = {
        "url": url,
        "step": 2,
        "filled": {"#first_name": "Sameer", "#last_name": "Bagul"},
    }

    ticket_id = create_hitl_ticket(
        job_url=url,
        unanswered_questions=questions,
        dom_checkpoint=dom_checkpoint,
        gmail_thread_id="thread_12345",
        gmail_message_id="msg_98765",
        conn=conn,
    )
    assert ticket_id > 0

    pending = get_pending_hitl_tickets(conn=conn)
    assert len(pending) == 1
    assert pending[0]["ticket_id"] == ticket_id
    assert pending[0]["gmail_thread_id"] == "thread_12345"
    assert len(pending[0]["unanswered_questions"]) == 2
    assert pending[0]["dom_checkpoint"]["step"] == 2

    # Resolve ticket
    assert resolve_hitl_ticket(ticket_id, status="resolved", conn=conn) is True
    ticket = get_hitl_ticket(ticket_id, conn=conn)
    assert ticket["status"] == "resolved"
    assert ticket["resolved_at"] is not None

    # Now pending should be empty
    assert len(get_pending_hitl_tickets(conn=conn)) == 0


def test_ats_session_vault(fresh_db):
    conn, _ = fresh_db
    v_id = save_session_vault(
        ats_type="workday",
        company_domain="acme.myworkdayjobs.com",
        storage_state_path="/tmp/state_acme.json",
        account_email="sameer@example.com",
        conn=conn,
    )
    assert v_id > 0

    vault_entry = get_session_vault("workday", "acme.myworkdayjobs.com", conn=conn)
    assert vault_entry is not None
    assert vault_entry["account_email"] == "sameer@example.com"
    assert vault_entry["session_valid"] == 1

    # Invalidate session
    clear_session_vault("workday", "acme.myworkdayjobs.com", conn=conn)
    assert get_session_vault("workday", "acme.myworkdayjobs.com", conn=conn) is None


def test_pattern_rules(fresh_db):
    conn, _ = fresh_db
    r_id = store_pattern_rule(
        rule_name="phone_us_cleanup",
        label_regex=r"(?i)phone|mobile",
        field_type="tel",
        transform_expression="re.sub(r'[^0-9+]', '', val)",
        confidence=0.98,
        conn=conn,
    )
    assert r_id > 0

    rules = get_pattern_rules(conn=conn)
    assert len(rules) == 1
    assert rules[0]["rule_name"] == "phone_us_cleanup"
    assert rules[0]["hit_count"] == 0

    increment_pattern_rule_hit(r_id, conn=conn)
    rules_updated = get_pattern_rules(conn=conn)
    assert rules_updated[0]["hit_count"] == 1


def test_enhanced_store_qa_and_lookup_by_hash(fresh_db):
    conn, _ = fresh_db
    qa_id = store_qa(
        question="Do you require visa sponsorship now or in the future?",
        answer="No, I am legally authorized to work without sponsorship.",
        source="human_email",
        canonical_question="visa_sponsorship",
        option_synonyms=["No sponsorship required", "Authorized without visa", "Citizen / PR"],
        category="work_auth",
        conn=conn,
    )
    assert qa_id is not None

    import hashlib
    expected_hash = hashlib.sha256("visa_sponsorship".encode("utf-8")).hexdigest()
    results = lookup_qa_by_hash(expected_hash, conn=conn)
    assert len(results) == 1
    assert results[0]["canonical_question"] == "visa_sponsorship"
    assert results[0]["category"] == "work_auth"
    assert results[0]["source"] == "human_email"
    assert "No sponsorship required" in results[0]["option_synonyms"]


def test_concurrent_wal_writes(fresh_db):
    """Verify that multiple threads can write concurrently using write_with_retry in WAL mode."""
    _, db_file = fresh_db

    errors = []

    def writer_worker(worker_id):
        try:
            local_conn = sqlite3.connect(str(db_file), timeout=10.0)
            local_conn.execute("PRAGMA journal_mode=WAL")
            for i in range(15):
                url = f"https://example.com/worker-{worker_id}-job-{i}"
                local_conn.execute(
                    "INSERT INTO jobs (url, title, state) VALUES (?, ?, 'discovered')",
                    (url, f"Job {i}"),
                )
                local_conn.commit()
            local_conn.close()
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=writer_worker, args=(wid,)) for wid in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Concurrent WAL write encountered errors: {errors}"

    check_conn = sqlite3.connect(str(db_file))
    count = check_conn.execute("SELECT COUNT(*) FROM jobs WHERE url LIKE 'https://example.com/worker-%'").fetchone()[0]
    assert count == 4 * 15
    check_conn.close()
