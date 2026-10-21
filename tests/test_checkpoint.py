"""Unit tests for form state checkpointing and cookie vault storage."""

import json
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from applypilot.database import init_db
from applypilot.hitl.checkpoint import (
    serialize_form_checkpoint,
    save_browser_session_cookies,
    load_browser_session_cookies,
)


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_cp.db"
    conn = init_db(db_file)
    return conn


def test_serialize_form_checkpoint():
    url = "https://job-boards.greenhouse.io/acme/jobs/123"
    filled = {
        "input#first_name": "Sameer",
        "input#last_name": "Bagul",
        "input#email": "sameer@example.com",
    }
    unresolved = [
        {"field_id": "q1", "label": "Security Clearance", "type": "select", "options": ["Yes", "No"]},
    ]

    cp = serialize_form_checkpoint(
        page_url=url,
        step_index=2,
        filled_fields=filled,
        unresolved_questions=unresolved,
        extra_state={"scroll_y": 450},
    )

    assert cp["page_url"] == url
    assert cp["step_index"] == 2
    assert cp["filled_fields"]["input#first_name"] == "Sameer"
    assert len(cp["unresolved_questions"]) == 1
    assert cp["extra_state"]["scroll_y"] == 450
    assert "captured_at" in cp


def test_save_and_load_browser_session_cookies(test_db, tmp_path):
    cookies = [
        {"name": "session_id", "value": "xyz123abc", "domain": "acme.myworkdayjobs.com"},
        {"name": "auth_token", "value": "token_999", "domain": "acme.myworkdayjobs.com"},
    ]

    saved_path = save_browser_session_cookies(
        cookies=cookies,
        ats_type="workday",
        company_domain="acme.myworkdayjobs.com",
        account_email="sameer@example.com",
        storage_dir=tmp_path / "sessions",
        conn=test_db,
    )

    assert Path(saved_path).exists()

    loaded = load_browser_session_cookies("workday", "acme.myworkdayjobs.com", conn=test_db)
    assert loaded is not None
    assert len(loaded) == 2
    assert loaded[0]["name"] == "session_id"
    assert loaded[0]["value"] == "xyz123abc"
