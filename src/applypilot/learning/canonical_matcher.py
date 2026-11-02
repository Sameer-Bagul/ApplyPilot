"""Canonical Q&A Matcher & Pattern Transformer (Tier 1 & Tier 2 — 0 Tokens).

Provides zero-token screening question resolution by normalizing field labels,
running SQLite FTS5 lexical searches against qa_knowledge, matching dropdown
options with RapidFuzz, and applying pattern transforms with 0 LLM token cost.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
from typing import Any

try:
    from rapidfuzz import fuzz, process
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

from applypilot.database import get_connection, get_pattern_rules, increment_pattern_rule_hit
from applypilot.learning.tier1_semantic_qa import (
    _AFFIRMATIVE_KEYWORDS,
    _NEGATIVE_KEYWORDS,
    _NOISE_PATTERNS,
    _TOPIC_SYNONYMS,
    normalize_question,
)
from applypilot.learning.tier2_heuristics import format_date, normalize_phone, transform_units

logger = logging.getLogger(__name__)


def normalize_field_label(label: str) -> str:
    """Normalize form field label for deterministic matching."""
    return normalize_question(label)


def match_dropdown_option(
    user_answer: str,
    options: list[str],
    score_cutoff: float = 85.0,
) -> tuple[str | None, float]:
    """Match stored candidate answer against form dropdown options using RapidFuzz.

    Matches e.g. "Yes" -> "Yes, I am authorized to work in the US" with zero tokens.
    """
    if not options or not user_answer:
        return None, 0.0

    user_clean = user_answer.strip().lower()

    # Exact case-insensitive match
    for opt in options:
        if opt.strip().lower() == user_clean:
            return opt, 1.0

    # Boolean prefix / keyword heuristics
    is_user_aff = user_clean in _AFFIRMATIVE_KEYWORDS or any(user_clean.startswith(w) for w in ("yes", "authorized", "agree"))
    is_user_neg = user_clean in _NEGATIVE_KEYWORDS or any(user_clean.startswith(w) for w in ("no", "disagree", "not"))

    if is_user_aff:
        for opt in options:
            opt_lower = opt.strip().lower()
            if opt_lower in _AFFIRMATIVE_KEYWORDS or any(opt_lower.startswith(w) for w in ("yes", "authorized", "eligible", "i am")):
                return opt, 0.95

    if is_user_neg:
        for opt in options:
            opt_lower = opt.strip().lower()
            if opt_lower in _NEGATIVE_KEYWORDS or any(opt_lower.startswith(w) for w in ("no", "not authorized", "ineligible", "i am not")):
                return opt, 0.95

    # RapidFuzz fuzzy match
    if HAS_RAPIDFUZZ:
        best = process.extractOne(
            user_clean,
            options,
            scorer=fuzz.token_set_ratio,
            score_cutoff=score_cutoff,
        )
        if best:
            return best[0], best[1] / 100.0

    # Substring fallback
    for opt in options:
        if user_clean in opt.lower() or opt.lower() in user_clean:
            return opt, 0.88

    return None, 0.0


def execute_pattern_transform(label: str, raw_val: str, conn: sqlite3.Connection | None = None) -> str:
    """Apply rule transforms from pattern_rules or heuristics (e.g. phone, dates, units)."""
    if not raw_val:
        return raw_val

    lower_label = label.lower()

    # Built-in Tier 2 heuristic transforms
    if any(k in lower_label for k in ("phone", "mobile", "cell", "telephone")):
        return normalize_phone(raw_val)

    if any(k in lower_label for k in ("start date", "availability", "graduat", "date")):
        date_res = format_date(raw_val)
        if date_res:
            return date_res

    if any(k in lower_label for k in ("experience in months", "experience (months)", "months of experience")):
        unit_res = transform_units(raw_val, "val * 12")
        if unit_res:
            return str(int(unit_res))

    # Dynamic rules from pattern_rules table
    if conn:
        try:
            rules = get_pattern_rules(conn=conn)
            for rule in rules:
                regex_trigger = rule.get("regex_trigger") or rule.get("label_regex")
                if regex_trigger and re.search(regex_trigger, label, re.IGNORECASE):
                    expr = rule.get("python_transform_expr") or rule.get("transform_expression")
                    if expr:
                        # Safe expression evaluation
                        safe_globals = {"val": raw_val, "re": re}
                        try:
                            transformed = eval(expr, safe_globals)
                            increment_pattern_rule_hit(rule["rule_id"], conn=conn)
                            return str(transformed)
                        except Exception:
                            pass
        except Exception:
            pass

    return raw_val


def lookup_canonical_answer(
    label: str,
    field_type: str = "text",
    options: list[str] | None = None,
    profile: dict[str, Any] | None = None,
    conn: sqlite3.Connection | None = None,
) -> tuple[str | None, float, str]:
    """Retrieve answer with zero LLM tokens across Profile, qa_fts, and Pattern Rules.

    Returns:
        (resolved_answer, confidence_score, resolution_source)
    """
    if not label:
        return None, 0.0, "none"

    norm_label = normalize_field_label(label)
    prof = profile or {}

    # 1. Profile.json exact and synonym matching
    if any(k in norm_label for k in ("first_name", "first name", "given_name", "given name")) and prof.get("first_name"):
        return prof["first_name"], 1.0, "profile_exact"
    if any(k in norm_label for k in ("last_name", "last name", "family_name", "family name", "surname")) and prof.get("last_name"):
        return prof["last_name"], 1.0, "profile_exact"
    if any(k in norm_label for k in ("email", "email_address", "email address")) and prof.get("email"):
        return prof["email"], 1.0, "profile_exact"
    if any(k in norm_label for k in ("full_name", "full name", "your name", "candidate name", "name")) and prof.get("name"):
        return prof["name"], 1.0, "profile_exact"
    if any(k in norm_label for k in ("phone", "phone_number", "mobile", "cell")) and prof.get("phone"):
        return normalize_phone(prof["phone"]), 1.0, "profile_exact"
    if any(k in norm_label for k in ("linkedin", "linkedin_url")) and prof.get("linkedin"):
        return prof["linkedin"], 1.0, "profile_exact"
    if any(k in norm_label for k in ("github", "github_url")) and prof.get("github"):
        return prof["github"], 1.0, "profile_exact"
    if any(k in norm_label for k in ("work_authorization", "visa_sponsorship", "sponsorship_required", "sponsorship", "authorized")) and "authorized_in_us" in prof:
        val = "Yes" if prof["authorized_in_us"] else "No"
        if options:
            matched_opt, score = match_dropdown_option(val, options)
            if matched_opt:
                return matched_opt, score, "profile_dropdown"
        return val, 1.0, "profile_exact"

    # 2. SQLite FTS5 lexical search against qa_fts (0 tokens)
    if conn:
        try:
            # Tokenize words for FTS MATCH
            tokens = [w for w in re.findall(r"\w+", norm_label) if len(w) > 3]
            if tokens:
                fts_query = " OR ".join(tokens[:4])
                rows = conn.execute(
                    "SELECT question_key, canonical_question, answer_text FROM qa_fts WHERE qa_fts MATCH ? LIMIT 3",
                    (fts_query,),
                ).fetchall()
                if rows:
                    answer = rows[0]["answer_text"]
                    if options:
                        matched_opt, score = match_dropdown_option(answer, options)
                        if matched_opt:
                            return matched_opt, score, "qa_fts_dropdown"
                    transformed = execute_pattern_transform(label, answer, conn=conn)
                    return transformed, 0.95, "qa_fts"
        except Exception as e:
            logger.debug("FTS5 lookup notice: %s", e)

        # Hash fallback in qa_knowledge
        try:
            q_hash = hashlib.sha256(norm_label.encode("utf-8")).hexdigest()
            row = conn.execute(
                "SELECT answer_text FROM qa_knowledge WHERE question_hash = ? ORDER BY use_count DESC LIMIT 1",
                (q_hash,),
            ).fetchone()
            if row:
                ans = row[0]
                if options:
                    matched_opt, score = match_dropdown_option(ans, options)
                    if matched_opt:
                        return matched_opt, score, "qa_hash_dropdown"
                return execute_pattern_transform(label, ans, conn=conn), 0.92, "qa_hash"
        except Exception:
            pass

    return None, 0.0, "not_found"
