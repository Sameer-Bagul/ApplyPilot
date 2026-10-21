"""Tier 1: Canonical Q&A Hash & Semantic Lookup Engine.

Provides zero-token screening question resolution by normalizing question
text, matching against profile.json facts and SQLite qa_knowledge entries,
and canonicalizing dropdown options via RapidFuzz.
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

from applypilot.database import get_connection, lookup_qa, lookup_qa_by_hash

logger = logging.getLogger(__name__)

# Common boilerplate noise in ATS question labels
_NOISE_PATTERNS = [
    r"^\s*[\*\:\-\#\•\d\.\)\(\]]+\s*",      # leading bullets, numbers, asterisks
    r"\s*[\*\:\?]+$",                       # trailing punctuation, asterisks
    r"(?i)\b(please\s+(indicate|select|enter|provide|specify|choose|state))\b",
    r"(?i)\b(required|optional)\b",
    r"(?i)\b(do you|are you|will you|would you|have you)\b",
    r"(?i)\b(what is your|what's your|how many|how soon can you)\b",
]

# Canonical topic synonym mappings: regex -> canonical topic key
_TOPIC_SYNONYMS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"(?i)\b(visa|sponsorship|work authorization|authorized to work|legal authorization)\b"), "work_authorization"),
    (re.compile(r"(?i)\b(notice period|start date|how soon|availability)\b"), "notice_period"),
    (re.compile(r"(?i)\b(compensation|salary expectation|desired salary|desired pay|target salary|expected pay)\b"), "desired_salary"),
    (re.compile(r"(?i)\b(relocat\w*|willing to (move|relocate))\b"), "willing_to_relocate"),
    (re.compile(r"(?i)\b(clearance|security clearance|polygraph)\b"), "security_clearance"),
    (re.compile(r"(?i)\b(years of experience|total experience|work experience)\b"), "years_experience"),
    (re.compile(r"(?i)\b(degree|education level|highest level of education|highest degree)\b"), "education_level"),
    (re.compile(r"(?i)\b(gpa|grade point average)\b"), "gpa"),
    (re.compile(r"(?i)\b(hear about us|how did you hear|source of hire)\b"), "referral_source"),
    (re.compile(r"(?i)\b(remote|work from home|hybrid|on-site|office preference)\b"), "remote_preference"),
    (re.compile(r"(?i)\b(gender|race|ethnicity|hispanic|latino|veteran|disability)\b"), "eeo_survey"),
]

# Standard Boolean mappings
_AFFIRMATIVE_KEYWORDS = {"yes", "true", "authorized", "eligible", "willing", "agree", "i am", "y"}
_NEGATIVE_KEYWORDS = {"no", "false", "unauthorized", "ineligible", "unwilling", "disagree", "i am not", "n", "none"}


def normalize_question(text: str) -> str:
    """Normalize a question label for deterministic matching.

    Lowercases, strips punctuation and boilerplate, and maps key phrasing to
    canonical topic terms.
    """
    if not text:
        return ""
    # Strip HTML tags
    clean = re.sub(r"<[^>]+>", " ", text)
    # Strip noise phrases
    for pat in _NOISE_PATTERNS:
        clean = re.sub(pat, " ", clean)

    # Normalize whitespace & lower
    clean = " ".join(clean.lower().split())

    # Map to canonical topic keyword if a strong pattern matches
    for pat, canonical in _TOPIC_SYNONYMS:
        if pat.search(clean):
            return canonical

    return clean


def compute_question_hash(normalized_text: str) -> str:
    """Compute SHA-256 hash of normalized question text."""
    return hashlib.sha256(normalized_text.strip().lower().encode("utf-8")).hexdigest()


# Domain-specific synonym groups for common ATS dropdown options
_DROPDOWN_SYNONYM_GROUPS: list[set[str]] = [
    {"bachelor", "bachelors", "ba", "bs", "b.s.", "b.a.", "undergraduate", "4-year"},
    {"master", "masters", "ms", "m.s.", "ma", "m.a.", "graduate", "master of science", "master of arts"},
    {"phd", "ph.d.", "doctorate", "doctoral"},
    {"immediate", "immediately", "0 days", "none", "asap"},
    {"full-time", "full time", "permanent"},
    {"part-time", "part time"},
    {"hybrid", "remote / hybrid", "hybrid / remote"},
]


def match_dropdown_option(candidate_value: str, available_options: list[str],
                          threshold: float = 70.0) -> str | None:
    """Find the best matching option from a form's available dropdown options.

    Uses RapidFuzz token matching, domain synonym expansion, and Boolean mapping.
    """
    if not candidate_value or not available_options:
        return None

    norm_candidate = candidate_value.strip().lower()

    # 1. Exact case-insensitive match
    for opt in available_options:
        if opt.strip().lower() == norm_candidate:
            return opt

    # 2. Check for Boolean Yes/No matching
    is_cand_yes = norm_candidate in _AFFIRMATIVE_KEYWORDS or norm_candidate.startswith("yes")
    is_cand_no = norm_candidate in _NEGATIVE_KEYWORDS or norm_candidate.startswith("no")

    if is_cand_yes or is_cand_no:
        for opt in available_options:
            norm_opt = opt.strip().lower()
            if is_cand_yes:
                if norm_opt in {"yes", "y", "authorized", "i am authorized", "true"}:
                    return opt
                if norm_opt.startswith("yes"):
                    return opt
            elif is_cand_no:
                if norm_opt in {"no", "n", "not authorized", "false", "none", "decline to state"}:
                    return opt
                if norm_opt.startswith("no"):
                    return opt

    # 3. Check domain synonym groups (e.g. Master of Science -> Master's Degree)
    c_clean = re.sub(r"[^a-zA-Z0-9\s]", " ", norm_candidate).lower()
    c_tokens = set(c_clean.split())
    for opt in available_options:
        o_clean = re.sub(r"[^a-zA-Z0-9\s]", " ", opt.lower())
        o_tokens = set(o_clean.split())
        for grp in _DROPDOWN_SYNONYM_GROUPS:
            if any(s in c_clean or s in c_tokens for s in grp) and any(s in o_clean or s in o_tokens for s in grp):
                return opt

    # 4. Alphanumeric substring / acronym match (e.g. "PhD" in "Doctorate (Ph.D.)")
    c_alpha = re.sub(r"[^a-zA-Z0-9]", "", norm_candidate)
    if len(c_alpha) >= 2:
        for opt in available_options:
            o_alpha = re.sub(r"[^a-zA-Z0-9]", "", opt.lower())
            if c_alpha in o_alpha or o_alpha in c_alpha:
                return opt

    # 5. RapidFuzz multi-metric matching
    best_opt = None
    best_score = 0.0

    if HAS_RAPIDFUZZ:
        for opt in available_options:
            s_set = fuzz.token_set_ratio(norm_candidate, opt)
            s_part = fuzz.partial_ratio(norm_candidate, opt)
            s_w = fuzz.WRatio(norm_candidate, opt)
            score = max(s_set, s_part, s_w)
            if score > best_score and score >= threshold:
                best_score = score
                best_opt = opt
        return best_opt

    # Pure Python fallback
    cand_tokens = set(re.findall(r"\w+", norm_candidate))
    for opt in available_options:
        opt_tokens = set(re.findall(r"\w+", opt.lower()))
        if not opt_tokens:
            continue
        intersection = cand_tokens.intersection(opt_tokens)
        score = (len(intersection) / max(len(cand_tokens), 1)) * 100.0
        if score > best_score and score >= threshold:
            best_score = score
            best_opt = opt
    return best_opt

    return None


def _check_profile_for_topic(topic: str, profile: dict) -> tuple[Any, float]:
    """Look up a topic in structured candidate profile."""
    if not profile:
        return None, 0.0

    # Direct keys
    if topic == "work_authorization":
        auth = profile.get("work_authorization") or profile.get("visa_status")
        if isinstance(auth, dict):
            # E.g. {"us_authorized": True, "requires_sponsorship": False}
            if auth.get("requires_sponsorship") is False:
                return "Yes, legally authorized without sponsorship", 1.0
            return "Requires sponsorship", 1.0
        if isinstance(auth, str):
            return auth, 1.0
        if profile.get("requires_sponsorship") is not None:
            return ("No" if not profile.get("requires_sponsorship") else "Yes"), 1.0

    elif topic == "notice_period":
        val = profile.get("notice_period") or profile.get("availability")
        if val:
            return str(val), 1.0

    elif topic == "desired_salary":
        val = profile.get("desired_salary") or profile.get("target_salary") or profile.get("compensation")
        if val:
            return str(val), 1.0

    elif topic == "willing_to_relocate":
        val = profile.get("willing_to_relocate") or profile.get("relocation")
        if val is not None:
            return ("Yes" if val else "No"), 1.0

    elif topic == "security_clearance":
        val = profile.get("security_clearance")
        if val is not None:
            return str(val), 1.0

    elif topic == "years_experience":
        val = profile.get("years_of_experience") or profile.get("total_experience")
        if val is not None:
            return str(val), 1.0

    elif topic == "education_level":
        edu = profile.get("education") or profile.get("highest_degree")
        if isinstance(edu, list) and edu:
            return edu[0].get("degree", "Bachelor's Degree"), 1.0
        if isinstance(edu, str):
            return edu, 1.0

    elif topic == "referral_source":
        return profile.get("referral_source", "Job Board / LinkedIn"), 0.95

    elif topic == "remote_preference":
        return profile.get("work_preference", "Remote / Hybrid"), 0.95

    return None, 0.0


def resolve_screening_question(question_text: str,
                                field_type: str | None = None,
                                options: list[str] | None = None,
                                profile: dict | None = None,
                                conn: sqlite3.Connection | None = None) -> tuple[str | None, float, str]:
    """Resolve a screening question without LLM tokens.

    Returns:
        (resolved_value, confidence, match_source)
        match_source is 'profile', 'qa_hash', 'qa_exact', 'qa_fuzzy', or 'unresolved'.
    """
    if not question_text:
        return None, 0.0, "unresolved"

    if conn is None:
        conn = get_connection()

    norm_q = normalize_question(question_text)
    q_hash = compute_question_hash(norm_q)

    candidate_value = None
    confidence = 0.0
    match_source = "unresolved"

    # Step 1: Check canonical topic in candidate profile
    if profile:
        val, conf = _check_profile_for_topic(norm_q, profile)
        if val is not None and conf > 0.0:
            candidate_value = val
            confidence = conf
            match_source = "profile"

    # Step 2: Check qa_knowledge by canonical hash
    if candidate_value is None:
        hash_rows = lookup_qa_by_hash(q_hash, conn=conn)
        if hash_rows:
            candidate_value = hash_rows[0].get("answer_text")
            confidence = 0.95
            match_source = "qa_hash"

    # Step 3: Check qa_knowledge by original question key
    if candidate_value is None:
        exact_rows = lookup_qa(question_text, conn=conn)
        if exact_rows:
            candidate_value = exact_rows[0].get("answer_text")
            confidence = 0.90
            match_source = "qa_exact"

    # Step 4: If we found a candidate value and options are specified (select/radio), map it
    if candidate_value is not None:
        if options:
            matched_option = match_dropdown_option(str(candidate_value), options)
            if matched_option:
                return matched_option, confidence, match_source
            else:
                logger.debug(
                    "Dropdown options %s could not be matched against candidate value '%s'",
                    options, candidate_value,
                )
                return None, 0.0, "unresolved"
        return str(candidate_value), confidence, match_source

    return None, 0.0, "unresolved"
