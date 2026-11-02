"""Self-evolving zero-token progression learning engine.

Contains:
- Tier 0: Deterministic Playwright selector execution & selector replay cache
- Tier 1: Canonical Q&A lexical matching (FTS5 + RapidFuzz)
- Tier 2: Heuristics, date/phone formatting, and pattern rule transforms
- Trace analyzer & pattern compiler: Post-run promotion (applypilot learn)
"""

from applypilot.learning.tier0_playbook import (
    detect_form_ats,
    get_tier0_field_mappings,
    fill_standard_fields_playwright,
)
from applypilot.learning.tier0_replay import (
    compute_page_step_signature,
    get_cached_selectors_for_step,
    replay_tier0_cached_actions,
)
from applypilot.learning.canonical_matcher import (
    normalize_field_label,
    lookup_canonical_answer,
    match_dropdown_option,
    execute_pattern_transform,
)
from applypilot.learning.tier1_semantic_qa import (
    normalize_question,
    compute_question_hash,
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
from applypilot.learning.trace_analyzer import (
    analyze_and_promote_traces,
)
from applypilot.learning.migrations import (
    run_migrations,
)

__all__ = [
    "detect_form_ats",
    "get_tier0_field_mappings",
    "fill_standard_fields_playwright",
    "compute_page_step_signature",
    "get_cached_selectors_for_step",
    "replay_tier0_cached_actions",
    "normalize_field_label",
    "lookup_canonical_answer",
    "match_dropdown_option",
    "execute_pattern_transform",
    "normalize_question",
    "compute_question_hash",
    "resolve_screening_question",
    "normalize_phone",
    "format_date",
    "transform_units",
    "promote_successful_traces",
    "record_apply_trace",
    "analyze_and_promote_traces",
    "run_migrations",
]
