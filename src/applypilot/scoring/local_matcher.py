"""Local Deterministic Algorithmic Matcher for ApplyPilot.

Provides fast, zero-token, zero-external-LLM matching between candidate profiles
and discovered job postings. Evaluates 4 dimensions:
1. Title / Role Match (35%)
2. Technical Skills & Stack Overlap (35%)
3. Seniority Fit (15%)
4. Location & Work Mode Fit (15%)

Computes scores on a 1-10 scale in milliseconds.
Never discards jobs: non-matching jobs are given lower scores but permanently preserved.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from applypilot.config import PROFILE_PATH, RESUME_PATH

logger = logging.getLogger(__name__)

# Default candidate profile if profile.json is not initialized yet
DEFAULT_TARGET_ROLES = [
    "AI Engineer",
    "Machine Learning Engineer",
    "Fullstack Engineer",
    "Full Stack Developer",
    "Backend Engineer",
    "Python Developer",
    "Software Engineer",
    "Platform Engineer",
    "DevOps Engineer",
]

DEFAULT_TARGET_SKILLS = [
    "python",
    "fastapi",
    "react",
    "typescript",
    "javascript",
    "docker",
    "kubernetes",
    "aws",
    "gcp",
    "postgresql",
    "mongodb",
    "sql",
    "git",
    "linux",
    "ci/cd",
    "llm",
    "langchain",
    "agentic-ai",
    "rest",
    "graphql",
]

DEFAULT_TARGET_LOCATIONS = ["remote", "pune", "bengaluru", "bangalore", "hyderabad", "india", "worldwide"]

SENIORITY_KEYWORDS = {
    "lead": ["lead", "staff", "principal", "head", "architect"],
    "senior": ["senior", "sr", "sr.", "experienced", "expert"],
    "middle": ["mid", "intermediate", "software engineer", "developer", "engineer ii", "level 2"],
    "junior": ["junior", "jr", "entry", "intern", "associate", "trainee", "fresher"],
}


def load_candidate_criteria() -> dict[str, Any]:
    """Load target criteria from profile.json, falling back to rich defaults."""
    criteria: dict[str, Any] = {
        "target_roles": list(DEFAULT_TARGET_ROLES),
        "target_skills": list(DEFAULT_TARGET_SKILLS),
        "target_locations": list(DEFAULT_TARGET_LOCATIONS),
        "target_seniority": "senior",
    }

    if PROFILE_PATH.exists():
        try:
            profile_data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
            # Experience / role
            exp = profile_data.get("experience", {})
            if exp.get("target_role"):
                criteria["target_roles"].insert(0, exp["target_role"])

            # Skills boundary
            sb = profile_data.get("skills_boundary", {})
            user_skills: list[str] = []
            for category_skills in sb.values():
                if isinstance(category_skills, list):
                    user_skills.extend([s.lower() for s in category_skills])
            if user_skills:
                criteria["target_skills"] = list(set(user_skills + DEFAULT_TARGET_SKILLS))

            # Personal location
            personal = profile_data.get("personal", {})
            user_city = personal.get("city")
            if user_city:
                criteria["target_locations"].insert(0, user_city.lower())
        except Exception as e:
            logger.debug("Notice reading profile.json in local matcher: %s", e)

    # Also parse skills from resume.txt if present
    if RESUME_PATH.exists():
        try:
            resume_text = RESUME_PATH.read_text(encoding="utf-8").lower()
            for skill in DEFAULT_TARGET_SKILLS:
                if skill in resume_text and skill not in criteria["target_skills"]:
                    criteria["target_skills"].append(skill)
        except Exception:
            pass

    return criteria


def _clean_tokens(text: str) -> set[str]:
    """Split text into lowercase alphanumeric tokens."""
    if not text:
        return set()
    return set(re.findall(r"\b[a-zA-Z0-9_\-+#]{2,}\b", text.lower()))


def score_title_match(job_title: str, target_roles: list[str]) -> tuple[float, str]:
    """Score title alignment from 0 to 10."""
    if not job_title:
        return 2.0, "Missing job title"

    title_lower = job_title.lower()

    # Immediate negative filter: pure sales, hr, legal, marketing, medical
    non_tech_patterns = [
        r"\brecruiter\b", r"\btalent acquisition\b", r"\bhuman resources\b",
        r"\baccount executive\b", r"\bsales representative\b", r"\bmarketing manager\b",
        r"\bgraphic designer\b", r"\bnurse\b", r"\bphysician\b", r"\bpharmacist\b",
        r"\blegal counsel\b", r"\bparalegal\b",
    ]
    for pattern in non_tech_patterns:
        if re.search(pattern, title_lower):
            return 1.5, "Non-technical domain"

    # Exact or near-exact target role match
    title_tokens = _clean_tokens(title_lower)
    for role in target_roles:
        role_tokens = _clean_tokens(role.lower())
        if role_tokens.issubset(title_tokens):
            return 10.0, f"Exact role match: '{role}'"

    # Engineering / technical title overlap
    tech_hits = 0
    strong_tech = ["ai", "machine learning", "fullstack", "backend", "python", "software", "platform", "cloud", "devops", "systems", "data", "engineer", "developer"]
    matched_words = []
    for st in strong_tech:
        if st in title_lower:
            tech_hits += 1
            matched_words.append(st)

    if tech_hits >= 3:
        return 9.0, f"Strong technical match: {', '.join(matched_words)}"
    elif tech_hits == 2:
        return 7.5, f"Moderate technical match: {', '.join(matched_words)}"
    elif tech_hits == 1:
        return 5.5, f"Partial technical match: {', '.join(matched_words)}"

    return 3.0, "Low role overlap"


def score_skills_overlap(job_text: str, target_skills: list[str]) -> tuple[float, list[str]]:
    """Score tech stack alignment from 0 to 10 and return matched keywords."""
    if not job_text:
        return 4.0, []

    text_lower = job_text.lower()
    matched_skills = []

    for skill in target_skills:
        # Regex boundary check so e.g. "go" doesn't match "good"
        escaped = re.escape(skill)
        pattern = rf"(?:\b|_){escaped}(?:\b|_)"
        if re.search(pattern, text_lower):
            matched_skills.append(skill)

    count = len(matched_skills)
    if count >= 8:
        score = 10.0
    elif count >= 6:
        score = 8.5
    elif count >= 4:
        score = 7.0
    elif count >= 2:
        score = 5.0
    elif count == 1:
        score = 3.5
    else:
        score = 2.0

    return score, matched_skills


def score_seniority_fit(job_title: str, job_text: str, target_seniority: str = "senior") -> float:
    """Score seniority alignment from 0 to 10."""
    combined = f"{job_title} {job_text[:500]}".lower()

    is_lead = any(w in combined for w in SENIORITY_KEYWORDS["lead"])
    is_senior = any(w in combined for w in SENIORITY_KEYWORDS["senior"])
    is_junior = any(w in combined for w in SENIORITY_KEYWORDS["junior"])

    if target_seniority in ("senior", "lead"):
        if is_senior or is_lead:
            return 10.0
        if is_junior:
            return 3.0
        return 7.0  # unspecified or standard mid-level

    return 7.0


def score_location_fit(location: str | None, target_locations: list[str]) -> float:
    """Score location / work mode from 0 to 10."""
    if not location:
        return 6.0  # unknown, give benefit of the doubt

    loc_lower = location.lower()

    # Remote or anywhere is highest fit
    if any(r in loc_lower for r in ("remote", "anywhere", "wfh", "distributed", "global", "work from home")):
        return 10.0

    # Matches target city / country
    for t_loc in target_locations:
        if t_loc.lower() in loc_lower:
            return 9.5

    # Other locations
    return 4.0


def calculate_local_fit_score(
    title: str,
    description: str | None,
    location: str | None = None,
    criteria: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Calculate deterministic job fit score on a 1-10 scale.

    Returns:
        {
            "fit_score": int (1-10),
            "raw_score": float,
            "eligibility": "eligible" | "low_fit",
            "matched_keywords": list[str],
            "score_reasoning": str,
        }
    """
    if criteria is None:
        criteria = load_candidate_criteria()

    s_title, title_reason = score_title_match(title, criteria["target_roles"])
    s_skills, matched_keywords = score_skills_overlap(description or "", criteria["target_skills"])
    s_seniority = score_seniority_fit(title, description or "", criteria["target_seniority"])
    s_location = score_location_fit(location, criteria["target_locations"])

    # Weighted formula: Title 35%, Skills 35%, Seniority 15%, Location 15%
    raw_score = (
        (s_title * 0.35)
        + (s_skills * 0.35)
        + (s_seniority * 0.15)
        + (s_location * 0.15)
    )

    final_score = int(round(raw_score))
    final_score = max(1, min(10, final_score))

    kw_str = ", ".join(matched_keywords[:10]) if matched_keywords else "none"
    reasoning = (
        f"Algorithmic match: {final_score}/10. {title_reason}. "
        f"Matched {len(matched_keywords)} core skills ({kw_str}). "
        f"Location rating: {s_location:.0f}/10."
    )

    eligibility = "eligible" if final_score >= 7 else "low_fit"

    return {
        "fit_score": final_score,
        "raw_score": round(raw_score, 2),
        "eligibility": eligibility,
        "matched_keywords": matched_keywords,
        "score_reasoning": reasoning,
    }

