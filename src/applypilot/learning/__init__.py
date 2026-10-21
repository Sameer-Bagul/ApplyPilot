"""Self-evolving zero-token progression learning engine.

Contains:
- Tier 0: Deterministic Playwright selector execution
- Tier 1: Semantic Q&A matching and canonical question normalization
- Tier 2: Heuristics, date/phone formatting, and unit conversion rules
- Pattern compiler: Stage 7 trace analyzer and cache promoter (applypilot learn)
"""

from applypilot.learning.tier0_playbook import (
    detect_form_ats,
    get_tier0_field_mappings,
    fill_standard_fields_playwright,
)
from applypilot.learning.tier1_semantic_qa import (
    normalize_question,
    compute_question_hash,
    match_dropdown_option,
    resolve_screening_question,
)
from applypilot.learning.tier2_heuristics import (
    normalize_phone,
    format_date,
    transform_units,
)
from applypilot.learning.pattern_compiler import (
    promote_successful_traces,
    record_apply_trace,
)

__all__ = [
    "detect_form_ats",
    "get_tier0_field_mappings",
    "fill_standard_fields_playwright",
    "normalize_question",
    "compute_question_hash",
    "match_dropdown_option",
    "resolve_screening_question",
    "normalize_phone",
    "format_date",
    "transform_units",
    "promote_successful_traces",
    "record_apply_trace",
]
