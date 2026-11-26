"""Multi-Dimensional Resume-to-JD Match Scorer for ApplyPilot.

Evaluates candidate fit against job metadata across 4 deterministic dimensions:
1. Technical Skills Overlap (40%)
2. Role Category Alignment (30%)
3. Experience Level Alignment (20%)
4. Workplace & Location Fit (10%)

Produces:
- 0–100 Composite Match Percentage
- 1–10 Fit Score for ApplyPilot database
- Matched vs Missing Skills breakdown
- UI Pills and Visual Badges
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from applypilot.config import APP_DIR, PROFILE_PATH
from applypilot.enrichment.metadata_extractor import extract_all_metadata

logger = logging.getLogger("applypilot.resume_matcher")

# Verified Candidate Baseline (Sameer Bagul)
CANDIDATE_SKILLS_SET = {
    "python", "fastapi", "react", "typescript", "javascript", "next.js", "docker",
    "kubernetes", "postgresql", "sql", "redis", "llm", "langchain", "langgraph",
    "pytorch", "aws", "git", "linux", "ci/cd", "playwright", "rest", "graphql",
    "microservices", "agents", "rag", "vector db", "html/css", "tailwind",
}

CANDIDATE_YEARS_EXP = 2.5
CANDIDATE_TARGET_LOCATIONS = {
    "remote", "pune", "bangalore", "bengaluru", "mumbai", "delhi", "hyderabad",
    "gurgaon", "noida", "india", "worldwide", "anywhere", "wfh",
}


def load_candidate_profile() -> dict[str, Any]:
    """Load candidate profile from candidate_vault.json or profile.json."""
    vault_path = Path("config/candidate_vault.json")
    if vault_path.exists():
        try:
            data = json.loads(vault_path.read_text(encoding="utf-8"))
            return data
        except Exception:
            pass

    if PROFILE_PATH.exists():
        try:
            data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
            return data
        except Exception:
            pass

    return {
        "name": "Sameer Bagul",
        "years_of_experience": CANDIDATE_YEARS_EXP,
        "skills": list(CANDIDATE_SKILLS_SET),
        "target_roles": ["AI Engineer", "Fullstack Engineer", "Backend Engineer"],
    }


def compute_skill_overlap_score(tech_stack: list[str]) -> tuple[float, list[str], list[str]]:
    """Compute skill overlap score (0-40) and return (score, matched_skills, missing_skills)."""
    if not tech_stack:
        # If JD lists no specific technical keywords, provide a neutral baseline
        return 22.0, [], []

    matched: list[str] = []
    missing: list[str] = []

    for s in tech_stack:
        if s.lower() in CANDIDATE_SKILLS_SET:
            matched.append(s)
        else:
            missing.append(s)

    ratio = len(matched) / max(len(tech_stack), 1)
    # Scale to 40 points with a floor for partial coverage
    score = ratio * 40.0
    return score, matched, missing


def compute_role_alignment_score(category: str) -> float:
    """Compute role alignment score (0-30)."""
    if category in ("AI_ML", "FULLSTACK", "BACKEND", "GENERAL_SWE"):
        return 30.0
    if category in ("FRONTEND", "DATA_ENGINEERING", "DEVOPS_CLOUD"):
        return 22.0
    if category in ("MOBILE", "QA_TESTING"):
        return 12.0
    if category == "PRODUCT_MANAGEMENT":
        return 10.0
    if category == "NON_TECH":
        return 0.0
    return 8.0


def compute_experience_fit_score(exp_info: dict[str, Any]) -> tuple[float, str]:
    """Compute experience alignment score (0-20) and human-readable label."""
    min_years = exp_info.get("min_years", 0)
    level = exp_info.get("level", "Mid")

    if min_years == 0 and level in ("Junior", "Mid"):
        return 18.0, "Entry/Mid (Well Matched)"

    # Candidate has ~2.5 years of experience
    if min_years <= 3:
        return 20.0, f"{exp_info.get('raw_text', '0-3 yrs')} (Perfect Match)"
    elif min_years <= 5:
        return 16.0, f"{exp_info.get('raw_text', '3-5 yrs')} (Stretch Match)"
    elif min_years <= 7:
        return 8.0, f"{exp_info.get('raw_text', '5-7 yrs')} (Senior Requirement)"
    else:
        return 2.0, f"{exp_info.get('raw_text', '8+ yrs')} (Staff/Principal Level)"


def compute_location_fit_score(workplace_type: str, location_raw: str | None) -> float:
    """Compute workplace & geography alignment score (0-10)."""
    if workplace_type == "Remote":
        return 10.0

    loc_lower = (location_raw or "").lower()
    if any(city in loc_lower for city in CANDIDATE_TARGET_LOCATIONS):
        return 10.0

    if not location_raw or location_raw.lower() in ("unknown", "unspecified"):
        return 6.0

    # International Onsite (e.g. US/UK/EU onsite requiring relocation/visa)
    return 3.0


def evaluate_job_match(job: dict[str, Any], metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """Calculate multi-dimensional match rating from candidate profile to job posting.

    Args:
        job: Raw job dictionary from SQLite jobs table.
        metadata: Optional pre-extracted metadata from metadata_extractor.

    Returns:
        Structured match result with percentage, 1-10 score, reasoning, and visual tags.
    """
    if metadata is None:
        metadata = extract_all_metadata(job)

    # Immediate hard rejection for Non-Tech roles
    if metadata.get("is_non_tech"):
        return {
            "match_percentage": 0,
            "fit_score": 1,
            "badge": "🔴 0% (Non-Engineering)",
            "reasoning": f"Non-engineering position ({job.get('title', 'Unknown')}). Automatically flagged for exclusion.",
            "matched_skills": [],
            "missing_skills": [],
            "experience_label": "N/A",
            "metadata": metadata,
            "triage_action": "archive",
        }

    # 1. Tech Skills Overlap (40 pts)
    skill_score, matched_skills, missing_skills = compute_skill_overlap_score(metadata.get("tech_stack", []))

    # 2. Role Category (30 pts)
    role_score = compute_role_alignment_score(metadata.get("role_category", "OTHER_TECH"))

    # 3. Experience Alignment (20 pts)
    exp_score, exp_label = compute_experience_fit_score(metadata.get("experience", {}))

    # 4. Location & Workplace (10 pts)
    loc_score = compute_location_fit_score(metadata.get("workplace_type", "Onsite"), metadata.get("location_raw"))

    # Total composite
    total_score = skill_score + role_score + exp_score + loc_score
    match_pct = max(0, min(100, round(total_score)))
    fit_score = max(1, min(10, round(match_pct / 10)))

    # Determine badge and color
    if match_pct >= 80:
        badge = f"🟢 {match_pct}% Strong Match"
        triage = "ready_to_apply"
    elif match_pct >= 60:
        badge = f"🟡 {match_pct}% Moderate Match"
        triage = "viable"
    else:
        badge = f"🔴 {match_pct}% Low Match"
        triage = "low_fit"

    # Construct clean reasoning text
    matched_str = ", ".join(matched_skills[:6]) if matched_skills else "none specified"
    missing_str = f" | Missing: {', '.join(missing_skills[:4])}" if missing_skills else ""
    reasoning = (
        f"Match: {match_pct}% ({badge}). Role: {metadata.get('role_category_label')}. "
        f"Matched: {matched_str}{missing_str}. "
        f"Experience: {exp_label}. Workplace: {metadata.get('workplace_type')}."
    )

    # Generate UI pills
    pills = [metadata.get("workplace_type", "Onsite")]
    if metadata.get("experience", {}).get("level"):
        pills.append(f"{metadata['experience']['level']} Level")
    for s in matched_skills[:4]:
        pills.append(f"{s} ✓")
    for s in missing_skills[:2]:
        pills.append(f"{s} ✗")

    return {
        "match_percentage": match_pct,
        "fit_score": fit_score,
        "badge": badge,
        "reasoning": reasoning,
        "pills": pills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "experience_label": exp_label,
        "metadata": metadata,
        "triage_action": triage,
    }
