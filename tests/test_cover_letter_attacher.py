"""Unit tests for automated cover letter generation, resolution, and form attachment."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from applypilot.learning.tier0_playbook import (
    _BASELINE_ATS_SELECTORS,
    fill_standard_fields_playwright,
    get_tier0_field_mappings,
)
from applypilot.learning.tier1_semantic_qa import (
    normalize_question,
    resolve_screening_question,
)
from applypilot.scoring.cover_letter import ensure_cover_letter_for_job


@pytest.fixture
def sample_profile():
    return {
        "name": "Jane Developer",
        "first_name": "Jane",
        "last_name": "Developer",
        "email": "jane@example.com",
        "phone": "+1-555-0199",
        "current_title": "Senior Backend Engineer",
        "summary": "Experienced engineer with expertise in distributed systems and cloud infrastructure.",
        "resume_facts": {
            "real_metrics": ["Scaled systems to 10k RPS", "Reduced latency by 45%"],
        },
    }


@pytest.fixture
def sample_job():
    return {
        "url": "https://boards.greenhouse.io/techcorp/jobs/987654",
        "title": "Staff Backend Engineer",
        "company": "TechCorp",
        "site": "greenhouse",
    }


def test_baseline_selectors_contain_cover_letter():
    """Verify that every major ATS configuration has cover letter selectors."""
    for ats in ["greenhouse", "lever", "ashby", "workable", "workday", "smartrecruiters", "custom_domain"]:
        mappings = _BASELINE_ATS_SELECTORS.get(ats, {})
        has_cl = "cover_letter_file" in mappings or "cover_letter_text" in mappings
        assert has_cl, f"ATS {ats} is missing cover letter baseline selectors"


def test_tier0_mappings_include_cover_letter():
    """Verify get_tier0_field_mappings outputs cover letter fields with correct actions."""
    mappings = get_tier0_field_mappings("greenhouse", "boards.greenhouse.io")
    target_keys = {m["target_key"]: m["action_type"] for m in mappings}
    assert "cover_letter_file" in target_keys
    assert target_keys["cover_letter_file"] == "upload"
    assert "cover_letter_text" in target_keys
    assert target_keys["cover_letter_text"] == "fill"


def test_normalize_cover_letter_questions():
    """Verify semantic normalization maps various cover letter phrasings to canonical topic."""
    phrases = [
        "Please provide a cover letter",
        "Upload or paste your cover letter",
        "Letter of motivation (optional)",
        "Motivation letter",
        "Personal Statement for this role",
    ]
    for phrase in phrases:
        topic = normalize_question(phrase)
        assert topic == "cover_letter", f"Phrase '{phrase}' failed to normalize to 'cover_letter'; got '{topic}'"


def test_resolve_screening_question_cover_letter(sample_profile):
    """Verify resolve_screening_question produces candidate cover letter text."""
    val, conf, can_key = resolve_screening_question(
        question_text="Please submit your cover letter or personal statement",
        profile=sample_profile,
    )
    assert val is not None
    assert conf >= 0.85
    assert can_key == "profile"
    assert "Jane Developer" in val or "Senior Backend Engineer" in val


def test_ensure_cover_letter_generation(sample_job, sample_profile, tmp_path):
    """Verify ensure_cover_letter_for_job generates and saves a valid cover letter."""
    with patch("applypilot.scoring.cover_letter.COVER_LETTER_DIR", tmp_path):
        cl_path, cl_text = ensure_cover_letter_for_job(
            job=sample_job,
            profile=sample_profile,
            conn=None,
        )
        assert cl_path is not None
        assert Path(cl_path).exists()
        assert cl_text is not None
        assert len(cl_text) > 50
        assert "TechCorp" in cl_text
        assert "Jane Developer" in cl_text


@pytest.mark.anyio
async def test_fill_standard_fields_attaches_cover_letter(tmp_path):
    """Verify fill_standard_fields_playwright uploads cover letter file and types text."""
    mock_cl_file = tmp_path / "Jane_Developer_CL.pdf"
    mock_cl_file.write_text("dummy pdf binary content")

    mock_page = MagicMock()
    mock_page.url = "https://boards.greenhouse.io/techcorp/jobs/987654"

    # Mock locator for cover_letter_file and cover_letter_text
    loc_file = MagicMock()
    loc_file.is_visible = AsyncMock(return_value=True)
    loc_file.first = loc_file

    loc_text = MagicMock()
    loc_text.is_visible = AsyncMock(return_value=True)
    loc_text.first = loc_text

    def mock_locator(sel):
        if "cover" in sel and "file" in sel:
            return loc_file
        if "cover" in sel and ("textarea" in sel or "text" in sel):
            return loc_text
        m = MagicMock()
        m.is_visible = AsyncMock(return_value=False)
        m.first = m
        return m

    mock_page.locator.side_effect = mock_locator
    mock_page.evaluate = AsyncMock(return_value=[])

    profile = {"first_name": "Jane", "last_name": "Developer"}

    with patch("applypilot.apply.human_input.human_upload", new=AsyncMock()) as mock_upload, \
         patch("applypilot.apply.human_input.human_type", new=AsyncMock()) as mock_type:

        res = await fill_standard_fields_playwright(
            page=mock_page,
            profile=profile,
            ats_type="greenhouse",
            domain="boards.greenhouse.io",
            resume_path=None,
            cover_letter_path=str(mock_cl_file),
            cover_letter_text="This is my tailored cover letter for TechCorp.",
        )

        assert "cover_letter_file" in res["filled"]
        assert res["filled"]["cover_letter_file"] == str(mock_cl_file)
        mock_upload.assert_called_once()

        assert "cover_letter_text" in res["filled"]
        assert res["filled"]["cover_letter_text"] == "This is my tailored cover letter for TechCorp."
        mock_type.assert_called_once()
