"""Unit tests for Stage 7 Pattern Compiler & Cache Promoter."""

import json
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from applypilot.database import init_db, get_selectors_for_domain
from applypilot.learning.pattern_compiler import (
    record_apply_trace,
    promote_successful_traces,
)


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_learn.db"
    conn = init_db(db_file)
    return conn


def test_record_apply_trace_and_promote(test_db, tmp_path):
    trace_file = tmp_path / "test_apply_trace.jsonl"

    # Record 2 successful traces and 1 failed validation
    record_apply_trace(
        ats_type="greenhouse",
        url="https://job-boards.greenhouse.io/databricks/jobs/1234",
        selector="input#custom_first_name",
        action_type="fill",
        target_key="profile.first_name",
        label="Legal First Name",
        validation_passed=True,
        log_path=trace_file,
    )
    record_apply_trace(
        ats_type="workday",
        url="https://acme.myworkdayjobs.com/en-US/Careers/job/456",
        selector="input[data-automation-id='legalNameSection_lastName']",
        action_type="fill",
        target_key="profile.last_name",
        label="Last Name",
        validation_passed=True,
        log_path=trace_file,
    )
    record_apply_trace(
        ats_type="greenhouse",
        url="https://job-boards.greenhouse.io/databricks/jobs/1234",
        selector="input#invalid_field",
        action_type="fill",
        target_key="profile.unknown",
        validation_passed=False,
        log_path=trace_file,
    )

    result = promote_successful_traces(trace_log_path=trace_file, conn=test_db)
    assert result["total_processed"] == 3
    assert result["promoted_count"] == 2
    assert result["by_ats"]["greenhouse"] == 1
    assert result["by_ats"]["workday"] == 1

    # Check that ats_selector_cache now contains the promoted selectors
    gh_selectors = get_selectors_for_domain("greenhouse", "job-boards.greenhouse.io", conn=test_db)
    assert any(s["css_or_aria_selector"] == "input#custom_first_name" for s in gh_selectors)

    wd_selectors = get_selectors_for_domain("workday", "*.myworkdayjobs.com", conn=test_db)
    assert any("legalNameSection_lastName" in s["css_or_aria_selector"] for s in wd_selectors)
