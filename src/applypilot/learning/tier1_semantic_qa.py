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
    (re.compile(r"(?i)\b(current compensation|current salary|current ctc|current pay|present ctc|present salary)\b"), "current_salary"),
    (re.compile(r"(?i)\b(compensation|salary expectation\w*|desired salary|desired pay|target salary|expected pay|expected ctc|expected salary)\b"), "desired_salary"),
    (re.compile(r"(?i)\b(salary negotiable|negotiable|flexible on salary|flexible on compensation)\b"), "salary_negotiable"),
    (re.compile(r"(?i)\b(relocat\w*|willing to (move|relocate))\b"), "willing_to_relocate"),
    (re.compile(r"(?i)\b(clearance|security clearance|polygraph)\b"), "security_clearance"),
    (re.compile(r"(?i)\b(years of experience|total experience|work experience)\b"), "years_experience"),
    (re.compile(r"(?i)\b(degree|education level|highest level of education|highest degree)\b"), "education_level"),
    (re.compile(r"(?i)\b(gpa|grade point average)\b"), "gpa"),
    (re.compile(r"(?i)\b(hear about us|how did you hear|how did you learn|source of hire|where did you find|referral)\b"), "referral_source"),
    (re.compile(r"(?i)\b(remote|work from home|hybrid|on-site|office preference)\b"), "remote_preference"),
    (re.compile(r"(?i)\b(current location|current city|present location|where are you located|location)\b"), "current_location"),
    (re.compile(r"(?i)\b(gender|race|ethnicity|hispanic|latino|veteran|disability)\b"), "eeo_survey"),
    (re.compile(r"(?i)\b(linkedin|linked in|linkedin profile|linkedin url)\b"), "linkedin_url"),
    (re.compile(r"(?i)\b(github|github profile|github url)\b"), "github_url"),
    (re.compile(r"(?i)\b(portfolio|personal website|website url|blog url)\b"), "portfolio_url"),
    (re.compile(r"(?i)\b(current employer|recent employer|current company|most recent company|where do you currently work|list your most recent employer)\b"), "current_company"),
    (re.compile(r"(?i)\b(current title|current role|current job title|headline)\b"), "current_title"),
    (re.compile(r"(?i)\b(cover\s*letter|letter\s+of\s+motivation|motivation\s+letter|personal\s+statement|note\s+to\s+hiring\s+manager)\b"), "cover_letter"),
    (re.compile(r"(?i)\b(sms consent|whatsapp consent|communication consent|consent|acknowledge|confirm|agree to terms|privacy policy)\b"), "consent_agreement"),
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
    # Split camelCase (e.g. smsConsent -> sms Consent)
    clean = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    # Strip HTML tags
    clean = re.sub(r"<[^>]+>", " ", clean)
    # Strip noise phrases
    for pat in _NOISE_PATTERNS:
        clean = re.sub(pat, " ", clean)

    # Strip trailing asterisks and non-alphanumeric punctuation (e.g. ✱, *, ?)
    clean = re.sub(r"[\s\*\:\?\.\,\;\!\u2731\u2732\u2733\u2734\u2735\u2736\u2737\u2738\u2739\u273a\u273b\u273c\u273d\u273e\u273f\u2740\u2741\u2742\u2743\u2744\u2745\u2746\u2747\u2748\u2749\u274a\u274b]+$", "", clean)

    # Normalize whitespace & lower
    clean = " ".join(clean.lower().split()).strip()

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
    {"given", "consent given", "agree", "yes", "i agree", "consent"},
    {"notgiven", "not given", "decline", "no", "disagree"},
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

    elif topic == "current_salary":
        val = profile.get("current_salary") or profile.get("current_ctc")
        if val:
            return str(val), 1.0
        comp = profile.get("compensation", {})
        if isinstance(comp, dict):
            c_val = comp.get("current_ctc") or comp.get("current_salary")
            if c_val:
                return str(c_val), 1.0
        return "₹7,00,000", 0.95

    elif topic == "salary_negotiable":
        return "Yes, flexible and open to negotiate based on company budget", 1.0

    elif topic == "desired_salary":
        val = profile.get("desired_salary") or profile.get("target_salary") or profile.get("compensation")
        if isinstance(val, dict):
            target = val.get("target_salary") or val.get("expected_salary")
            if target:
                return str(target), 1.0
        if val:
            return str(val), 1.0
        return "₹7,00,000 - ₹10,00,000", 0.95

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

    elif topic == "linkedin_url":
        val = profile.get("urls", {}).get("linkedin") or profile.get("linkedin_url") or profile.get("linkedin")
        if val:
            return str(val), 1.0

    elif topic == "github_url":
        val = profile.get("urls", {}).get("github") or profile.get("github_url") or profile.get("github")
        if val:
            return str(val), 1.0

    elif topic == "portfolio_url":
        val = profile.get("urls", {}).get("portfolio") or profile.get("portfolio_url") or profile.get("urls", {}).get("website")
        if val:
            return str(val), 1.0

    elif topic == "current_company":
        val = profile.get("current_company")
        if val:
            return str(val), 1.0

    elif topic == "current_title":
        val = profile.get("current_title") or profile.get("title")
        if val:
            return str(val), 1.0

    elif topic == "cover_letter":
        val = profile.get("cover_letter_text") or profile.get("cover_letter")
        if val:
            return str(val), 1.0
        name = profile.get("name") or profile.get("full_name") or "Candidate"
        title = profile.get("current_title") or "Software Engineer"
        summary = profile.get("summary") or f"Experienced {title} with background in production systems."
        return f"Dear Hiring Team,\n\nI am applying with strong enthusiasm for this position. As a {title}, {summary}\n\nSincerely,\n{name}", 0.95

    elif topic == "consent_agreement":
        return "given", 1.0

    elif topic == "current_location":
        val = profile.get("city") or profile.get("location") or profile.get("current_city")
        if isinstance(val, dict):
            parts = [val.get("city"), val.get("state"), val.get("country")]
            val = ", ".join([p for p in parts if p])
        if val:
            return str(val), 1.0
        return "Bangalore, India", 1.0

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

    # Step 2: Check project and story matrix in profile (stories & experiences)
    if candidate_value is None and profile:
        q_lower = question_text.lower()
        # Story questions (AI, Agentic workflows)
        if any(w in q_lower for w in ["agent", "agentic", "ai system", "ai companion", "companion"]):
            projects = profile.get("projects", [])
            for proj in projects:
                cat = (proj.get("category") or "").lower()
                desc = proj.get("shortDescription") or ""
                if "agent" in cat or "ai" in cat or "ai" in desc.lower():
                    candidate_value = f"{proj.get('title')}: {desc}"
                    confidence = 0.95
                    match_source = "profile_project"
                    break

        # Distributed systems, Kubernetes, Architecture
        elif any(w in q_lower for w in ["distributed system", "kubernetes", "cloud", "architecture", "scale", "infrastructure", "fleet"]):
            rules = profile.get("story_matrix", {}).get("rules", [])
            for rule in rules:
                tech = (rule.get("tech") or "").lower()
                domain = (rule.get("bridge_domain") or "").lower()
                if "kubernetes" in tech or "cloud" in domain or "container" in domain:
                    candidate_value = rule.get("story")
                    confidence = 0.95
                    match_source = "profile_story"
                    break

    # Step 3: Check candidate profile qa_knowledge list
    if candidate_value is None and profile:
        qa_list = profile.get("qa_knowledge", [])
        if isinstance(qa_list, list):
            stop_words = {"tell", "us", "about", "a", "an", "the", "you", "your", "have", "for", "with", "or", "in", "to", "and", "of", "what", "is", "are", "do", "can", "if", "please", "describe"}
            q_clean = norm_q.lower()
            q_words = {w for w in re.findall(r"\w+", q_clean) if len(w) > 2 and w not in stop_words}
            if q_words:
                for item in qa_list:
                    item_q = (item.get("q") or "").lower()
                    item_key = (item.get("key") or "").lower()
                    item_words = {w for w in re.findall(r"\w+", item_q + " " + item_key) if len(w) > 2 and w not in stop_words}
                    if item_words and len(q_words & item_words) >= 2:
                        candidate_value = item.get("a")
                        confidence = 0.95
                        match_source = "profile_qa"
                        break

    # Step 4: Check database qa_knowledge by canonical hash
    if candidate_value is None:
        hash_rows = lookup_qa_by_hash(q_hash, conn=conn)
        if hash_rows:
            candidate_value = hash_rows[0].get("answer_text")
            confidence = 0.95
            match_source = "qa_hash"

    # Step 5: Check database qa_knowledge by original question key
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


def resolve_screening_question_ai(
    question_text: str,
    field_type: str = "text",
    options: list[str] | None = None,
    profile: dict | None = None,
    job: dict | None = None,
    ats_type: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> tuple[str | None, float, str]:
    """Resolve an unanswered screening question using Gemini / OpenRouter LLM API.

    Automatically stores the generated answer in qa_knowledge and qa_fts for continuous
    self-learning and zero-token reuse on subsequent applications.

    Returns:
        (resolved_value, confidence, source)
    """
    if not question_text:
        return None, 0.0, "unresolved"

    from applypilot.database import store_qa
    import os

    has_key = any(os.environ.get(k) for k in ("GEMINI_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY"))
    if not has_key:
        logger.debug("No LLM API keys configured for hybrid Q&A fallback.")
        return None, 0.0, "unresolved"

    prof = profile or {}
    personal = prof.get("personal", {})
    name = personal.get("full_name") or prof.get("first_name", "") + " " + prof.get("last_name", "")
    current_title = prof.get("experience", {}).get("current_job_title") or prof.get("current_title", "Software Engineer")
    skills = prof.get("skills_boundary", {}) or prof.get("skills", [])
    work_auth = prof.get("work_authorization", {})
    years_exp = prof.get("experience", {}).get("years_of_experience_total") or prof.get("years_of_experience", "5+")
    location = prof.get("personal", {}).get("city") or prof.get("location", "Bangalore, India")

    profile_context = (
        f"Applicant Name: {name}\n"
        f"Current Role / Title: {current_title}\n"
        f"Years of Experience: {years_exp}\n"
        f"Primary Location: {location}\n"
        f"Work Authorization: {work_auth}\n"
        f"Skills / Background: {skills}\n"
    )
    if prof.get("cover_letter_text"):
        profile_context += f"Candidate Summary / Cover Note: {prof.get('cover_letter_text')[:400]}\n"

    job_context = ""
    if job:
        job_context = f"Applying to Company: {job.get('company', '')}, Role: {job.get('title', '')}\n"

    system_prompt = (
        "You are an expert AI application assistant answering a single job application screening question on behalf of the candidate. "
        "Your response must be truthful based on the candidate's profile, highly professional, and direct. "
        "Do NOT include conversational filler, greetings, or explanations. Return ONLY the answer value."
    )

    user_prompt = (
        f"{job_context}"
        f"Candidate Profile:\n{profile_context}\n"
        f"Question: \"{question_text}\"\n"
        f"Field Type: {field_type}\n"
    )
    if options:
        user_prompt += f"Available Options (choose the single best option): {options}\n"
    else:
        user_prompt += "Format: concise, direct answer (for textarea: 1-3 crisp sentences; for text/number/boolean: exact value only).\n"

    try:
        from applypilot.llm import LLMClient, _detect_provider
        base_url, model, api_key = _detect_provider(quality=False)
        client = LLMClient(base_url=base_url, model=model, api_key=api_key, quality=False)
        raw_ans = client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=350,
        ).strip()

        # Clean enclosing quotes or markdown backticks
        clean_ans = raw_ans.strip('`"\'').strip()

        # If options are present, canonicalize via RapidFuzz
        if options:
            matched = match_dropdown_option(clean_ans, options)
            if matched:
                clean_ans = matched
            elif options:
                # Fallback to closest option
                for opt in options:
                    if opt.lower() in clean_ans.lower():
                        clean_ans = opt
                        break

        if clean_ans:
            source_tag = "gemini_flash" if "gemini" in model.lower() else ("openrouter" if "openrouter" in base_url else "ai_llm")
            # Continuous self-learning: store in knowledge base for future zero-token reuse
            try:
                import json as _json
                store_qa(
                    question=question_text,
                    answer=clean_ans,
                    source=source_tag,
                    field_type=field_type,
                    options_json=_json.dumps(options) if options else None,
                    ats_slug=ats_type,
                    conn=conn,
                )
                logger.info("Hybrid AI Q&A resolved '%s' -> '%s' (saved to qa_knowledge)", question_text[:50], clean_ans[:50])
            except Exception as e:
                logger.debug("Failed saving AI resolved Q&A: %s", e)

            return clean_ans, 0.92, source_tag

    except Exception as e:
        logger.warning("Hybrid AI Q&A error for '%s': %s", question_text, e)

    return None, 0.0, "unresolved"

