import re
from typing import Dict, Any, Tuple

def safe_str(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, (list, tuple, set)):
        return " ".join(str(x) for x in val)
    return str(val)

def score_job(job: Dict[str, Any]) -> Tuple[int, str, Dict[str, Any]]:
    """
    Evaluates a job listing against Sameer Bagul's profile according to the Master Plan.
    Returns:
        (total_score: int [0-100], fit_tier: str ['Tier A', 'Tier B', 'Tier C'], breakdown: dict)
    """
    title = safe_str(job.get("job_title")).lower()
    skills = safe_str(job.get("required_skills")).lower()
    desc = safe_str(job.get("description")).lower()
    location = safe_str(job.get("location")).lower()
    exp = safe_str(job.get("experience_req")).lower()
    combined_text = f"{title} {skills} {desc}"

    # 1. Tech Stack Overlap (Max 40 points)
    tech_score = 0
    tech_details = []

    # LangGraph / Multi-agent / RAG (+25)
    agent_keywords = ["langgraph", "langchain", "multi-agent", "agentic", "rag", "retrieval augmented", "vector", "llm agent", "ai agent"]
    if any(k in combined_text for k in agent_keywords):
        tech_score += 25
        tech_details.append("LangGraph/Agentic/RAG (+25)")
    elif any(k in combined_text for k in ["genai", "generative ai", "llm", "prompt engineering"]):
        tech_score += 18
        tech_details.append("GenAI/LLMs (+18)")

    # Python backend (FastAPI / Django / APIs) (+15)
    py_keywords = ["python", "fastapi", "django", "flask", "backend", "rest api", "graphql"]
    if any(k in combined_text for k in py_keywords):
        tech_score += 15
        tech_details.append("Python Backend/FastAPI (+15)")

    # AI-native testing / Playwright (+10)
    test_keywords = ["playwright", "automation", "testing", "qa automation", "selenium", "eval", "evals", "evaluation"]
    if any(k in combined_text for k in test_keywords):
        tech_score += 10
        tech_details.append("Testing/Playwright/Evals (+10)")

    # Full-stack React / TypeScript / Node (+10)
    fs_keywords = ["react", "typescript", "node", "next.js", "full stack", "fullstack", "frontend"]
    if any(k in combined_text for k in fs_keywords):
        tech_score += 10
        tech_details.append("Full-Stack React/TS (+10)")

    tech_score = min(40, tech_score)

    # 2. Experience Alignment (Max 30 points)
    exp_score = 0
    exp_details = []

    # Check for senior / staff penalty first
    is_senior = any(k in title for k in ["senior", "sr.", "staff", "lead", "principal", "director", "architect"]) or any(k in exp for k in ["4+", "5+", "6+", "7+", "8+ years"])

    # 0-2 YOE / Junior / Associate / New Grad / Strong grads (+30)
    junior_match = any(k in title for k in ["junior", "associate", "intern", "grad", "entry", "fellow"]) or \
                   any(k in exp for k in ["0-", "1-", "0 to", "1 to", "new grad", "0-2", "1-2", "1-3", "freshers", "graduates"]) or \
                   "founding" in title

    if junior_match:
        exp_score = 30
        exp_details.append("Junior / 0-2 YOE / New Grad / Founding (+30)")
    elif any(k in exp for k in ["2-3", "2 to 3", "2+ years", "3 years"]):
        exp_score = 22
        exp_details.append("2-3 YOE Target (+22)")
    elif is_senior:
        exp_score = 10
        exp_details.append("Senior / Lead Role (Penalty applied: 10/30)")
    else:
        # Default mid/unspecified
        exp_score = 20
        exp_details.append("Standard Engineer Alignment (+20)")

    exp_score = min(30, max(0, exp_score))

    # 3. Location & Eligibility (Max 30 points)
    loc_score = 0
    loc_details = []

    if "pune" in location:
        loc_score = 30
        loc_details.append("Pune On-site / Hybrid (+30)")
    elif any(k in location for k in ["india", "bangalore", "bengaluru", "hyderabad", "remote india", "in"]):
        loc_score = 30
        loc_details.append("India Remote / Domestic (+30)")
    elif any(k in location for k in ["worldwide", "global", "anywhere", "remote worldwide", "remote"]):
        # Check if restricted to US/EU
        if any(k in location for k in ["us only", "usa only", "north america", "eu only", "europe only", "uk only"]):
            loc_score = 0
            loc_details.append("US/EU Restricted (0)")
        else:
            loc_score = 22
            loc_details.append("Worldwide Remote India-Eligible (+22)")
    else:
        loc_score = 15
        loc_details.append("Unspecified Location (+15)")

    loc_score = min(30, max(0, loc_score))

    total_score = tech_score + exp_score + loc_score

    # Determine Tier
    if total_score >= 85:
        tier = "Tier A"
    elif total_score >= 70:
        tier = "Tier B"
    else:
        tier = "Tier C"

    breakdown = {
        "total_score": total_score,
        "fit_tier": tier,
        "tech_score": tech_score,
        "tech_details": tech_details,
        "exp_score": exp_score,
        "exp_details": exp_details,
        "loc_score": loc_score,
        "loc_details": loc_details
    }

    return total_score, tier, breakdown
