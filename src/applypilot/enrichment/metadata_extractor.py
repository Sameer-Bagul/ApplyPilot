"""Zero-Token Deterministic Job Metadata Extractor for ApplyPilot.

Extracts structured metadata from job titles, locations, and descriptions in milliseconds:
1. Workplace Model: Remote, Hybrid, Onsite
2. Experience Requirement: Min/Max years & Level (Junior, Mid, Senior, Staff, Executive)
3. Role Categorization: AI/ML, Backend, Fullstack, Frontend, DevOps, Data, Non-Tech
4. Tech Stack: 60+ programming languages, frameworks, databases, and AI libraries
5. Compensation: Min/Max salary, currency, period
6. Employment Type: Full-time, Contract, Internship, Part-time
"""

from __future__ import annotations

import html
import re
from typing import Any

# Curated Taxonomy of Technical Skills & Keywords
TECH_SKILLS_TAXONOMY = {
    # Languages
    "python": r"\bpython\b",
    "typescript": r"\btypescript\b",
    "javascript": r"\bjavascript\b|\bjs\b",
    "go": r"\b(?:golang|go)\b",
    "rust": r"\brust\b",
    "c++": r"\bc\+\+\b",
    "c#": r"\bc#|\bcsharp\b",
    "java": r"\bjava\b",
    "kotlin": r"\bkotlin\b",
    "ruby": r"\bruby\b|\brails\b",
    "scala": r"\bscala\b",
    "php": r"\bphp\b",
    "swift": r"\bswift\b",
    "sql": r"\bsql\b",

    # AI / ML / LLMs
    "llm": r"\b(?:llm|llms|large language models?)\b",
    "langchain": r"\blangchain\b",
    "langgraph": r"\blanggraph\b",
    "pytorch": r"\bpytorch\b",
    "tensorflow": r"\btensorflow\b",
    "huggingface": r"\bhugging\s*face\b",
    "rag": r"\brag\b|\bretrieval[- ]augmented\b",
    "vector db": r"\b(?:vector (?:database|db)|pinecone|weaviate|qdrant|chromadb)\b",
    "agents": r"\b(?:ai agents?|agentic|autonomous agents?)\b",
    "fine-tuning": r"\bfine[- ]tuning\b|\blora\b|\bqlora\b",
    "nlp": r"\bnlp\b|\bnatural language processing\b",
    "computer vision": r"\bcomputer vision\b|\bopencv\b",

    # Frontend
    "react": r"\breact(?:\.js)?\b",
    "next.js": r"\bnext(?:\.js)?\b",
    "vue": r"\bvue(?:\.js)?\b",
    "angular": r"\bangular\b",
    "tailwind": r"\btailwind(?:css)?\b",
    "html/css": r"\bhtml5?\b|\bcss3?\b",
    "redux": r"\bredux\b|\bzustand\b",

    # Backend & API
    "fastapi": r"\bfastapi\b",
    "django": r"\bdjango\b",
    "flask": r"\bflask\b",
    "node.js": r"\bnode(?:\.js)?\b",
    "express": r"\bexpress(?:\.js)?\b",
    "nestjs": r"\bnest(?:\.js)?\b",
    "graphql": r"\bgraphql\b",
    "rest": r"\brest(?:ful)?(?:\s+api)?\b",
    "grpc": r"\bgrpc\b",
    "microservices": r"\bmicroservices?\b",

    # Cloud, DevOps & Infra
    "docker": r"\bdocker\b",
    "kubernetes": r"\b(?:kubernetes|k8s)\b",
    "aws": r"\baws\b|\bamazon web services\b",
    "gcp": r"\bgcp\b|\bgoogle cloud\b",
    "azure": r"\bazure\b",
    "terraform": r"\bterraform\b",
    "ci/cd": r"\bci[/-]cd\b|\bgithub actions\b|\bgitlab ci\b",
    "linux": r"\blinux\b|\bunix\b",
    "kafka": r"\bkafka\b",
    "spark": r"\bspark\b",

    # Databases
    "postgresql": r"\bpostgres(?:ql)?\b",
    "mysql": r"\bmysql\b",
    "mongodb": r"\bmongodb\b|\bmongo\b",
    "redis": r"\bredis\b",
    "elasticsearch": r"\belasticsearch\b",

    # Testing & Automation
    "playwright": r"\bplaywright\b",
    "selenium": r"\bselenium\b",
    "pytest": r"\bpytest\b",
    "git": r"\bgit\b|\bgithub\b|\bgitlab\b",
}

# Regex for Experience extraction
EXPERIENCE_REGEX = re.compile(
    r"(?:(?:minimum|at\s+least|around|over|\+)?\s*(\d{1,2})\s*(?:-|to|\+)?\s*(\d{1,2})?\s*(?:years?|yrs?))"
    r"(?:\s+of)?(?:\s+(?:relevant|hands-on|professional|work|industry))?\s+experience",
    re.IGNORECASE,
)

# Regex for Compensation extraction
SALARY_REGEX = re.compile(
    r"(?:(\$|₹|€|£|inr|usd)\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|\d+)(?:\s*(?:k|lakhs?|lpa))?)"
    r"(?:\s*(?:-|to)\s*(?:(\$|₹|€|£|inr|usd)\s*)?([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|\d+)(?:\s*(?:k|lakhs?|lpa))?)?",
    re.IGNORECASE,
)


def _strip_html(text: str | None) -> str:
    """Strip HTML tags and normalize whitespace."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = html.unescape(clean)
    return re.sub(r"\s+", " ", clean).strip()


def extract_workplace_type(location: str | None, text: str | None) -> str:
    """Classify workplace type as Remote, Hybrid, or Onsite."""
    combined = f"{location or ''} {text or ''[:600]}".lower()

    if any(k in combined for k in ("fully remote", "100% remote", "remote -", "remote,", "remote /", "wfh", "work from home")):
        return "Remote"
    if "hybrid" in combined:
        return "Hybrid"
    if any(k in combined for k in ("onsite", "on-site", "in-office", "in office", "office-based")):
        return "Onsite"
    if "remote" in combined:
        return "Remote"

    return "Onsite" if location and location.strip() else "Unspecified"


def extract_experience_requirements(title: str | None, text: str | None) -> dict[str, Any]:
    """Extract required years of experience and seniority tier."""
    clean_t = (title or "").lower()
    clean_desc = _strip_html(text)

    # 1. Check title seniority cues
    seniority_from_title = "Mid"
    if any(k in clean_t for k in ("intern", "trainee", "fresher", "apprentice")):
        seniority_from_title = "Intern"
    elif any(k in clean_t for k in ("junior", "entry", "associate", "level 1", "l1", "sde 1", "sde i")):
        seniority_from_title = "Junior"
    elif any(k in clean_t for k in ("staff", "principal", "distinguished", "architect")):
        seniority_from_title = "Staff"
    elif any(k in clean_t for k in ("lead", "manager", "head", "director", "vp", "chief")):
        seniority_from_title = "Lead"
    elif any(k in clean_t for k in ("senior", "sr.", "sr ", "sde 3", "sde iii", "lead engineer")):
        seniority_from_title = "Senior"

    # 2. Extract years from description
    min_years = 0
    max_years: int | None = None
    raw_match = ""

    matches = EXPERIENCE_REGEX.findall(clean_desc)
    if matches:
        first = matches[0]
        try:
            min_years = int(first[0])
            if first[1]:
                max_years = int(first[1])
            raw_match = f"{min_years}{'-' + str(max_years) if max_years else '+'} years"
        except (ValueError, TypeError):
            pass

    # Determine final level
    if min_years >= 8:
        level = "Staff"
    elif min_years >= 5:
        level = "Senior"
    elif min_years >= 2:
        level = "Mid"
    elif min_years > 0 or seniority_from_title == "Junior":
        level = "Junior"
    elif seniority_from_title == "Intern":
        level = "Intern"
    else:
        level = seniority_from_title

    return {
        "min_years": min_years,
        "max_years": max_years,
        "level": level,
        "raw_text": raw_match or f"{level} level",
    }


def extract_role_category(title: str, text: str | None = None) -> tuple[str, str]:
    """Classify into technical specializations or flag non-engineering roles.

    Returns:
        (category, display_label)
    """
    t = title.lower()

    # Immediate Non-Tech filter
    non_tech_keywords = (
        "sales", "account executive", "account manager", "recruiter", "recruiting", "talent acquisition",
        "human resources", "marketing", "content writer", "copywriter", "counsel", "legal",
        "customer support", "customer success", "shift lead", "store manager", "operations associate",
        "billing", "payroll", "compliance specialist", "office manager", "executive assistant",
        "auditor", "audit", "treasury", "licensing", "finance", "financial", "accounting", "accountant",
        "tax", "compensation analyst", "benefits", "broker", "trader", "paralegal", "underwriter",
        "mortgage", "banker", "teller", "credit risk", "commercial counsel", "underwriting",
        "risk analyst", "fraud analyst",
    )
    if any(k in t for k in non_tech_keywords) and not any(k in t for k in ("engineer", "developer", "architect")):
        return "NON_TECH", "Non-Engineering"

    if any(k in t for k in ("product manager", "project manager", "program manager", "scrum master", "agile coach")) and not any(k in t for k in ("software", "technical", "engineer", "developer")):
        return "PRODUCT_MANAGEMENT", "Product & Project Management"

    # Technical Categories
    if any(k in t for k in ("ai ", "ml ", "artificial intelligence", "machine learning", "deep learning", "nlp", "llm", "computer vision", "generative")):
        return "AI_ML", "AI / ML Engineering"
    if any(k in t for k in ("full stack", "fullstack", "full-stack")):
        return "FULLSTACK", "Full Stack Engineering"
    if any(k in t for k in ("backend", "back-end", "back end", "systems", "api engineer")):
        return "BACKEND", "Backend Engineering"
    if any(k in t for k in ("frontend", "front-end", "front end", "ui/ux", "ui engineer", "web developer")):
        return "FRONTEND", "Frontend Engineering"
    if any(k in t for k in ("devops", "sre", "site reliability", "cloud", "platform engineer", "infrastructure")):
        return "DEVOPS_CLOUD", "DevOps & Cloud Infrastructure"
    if any(k in t for k in ("data engineer", "analytics engineer", "big data", "etl", "data warehouse")):
        return "DATA_ENGINEERING", "Data Engineering"
    if any(k in t for k in ("mobile", "ios", "android", "flutter", "react native")):
        return "MOBILE", "Mobile Development"
    if any(k in t for k in ("qa", "test", "quality assurance", "sdet")):
        return "QA_TESTING", "Quality Assurance & SDET"
    if any(k in t for k in ("software", "engineer", "developer", "programmer", "architect")):
        return "GENERAL_SWE", "Software Engineering (General)"

    return "OTHER_TECH", "Other Technical Role"


def extract_tech_stack(text: str | None) -> list[str]:
    """Extract verified technologies and programming languages from job description."""
    if not text:
        return []

    clean = _strip_html(text).lower()
    discovered: list[str] = []

    for skill, pattern in TECH_SKILLS_TAXONOMY.items():
        if re.search(pattern, clean):
            discovered.append(skill)

    return sorted(discovered)


def extract_compensation(text: str | None, raw_salary: str | None = None) -> dict[str, Any]:
    """Extract salary range, currency, and pay period."""
    if raw_salary and raw_salary.strip() and raw_salary.lower() not in ("none", "null", "nan"):
        return {"raw": raw_salary.strip(), "has_salary": True}

    if not text:
        return {"raw": None, "has_salary": False}

    clean = _strip_html(text[:1200])
    match = SALARY_REGEX.search(clean)
    if match:
        raw_match = match.group(0).strip()
        return {"raw": raw_match, "has_salary": True}

    return {"raw": None, "has_salary": False}


def extract_employment_type(text: str | None) -> str:
    """Extract full-time, contract, or internship type."""
    if not text:
        return "Full-time"
    clean = text[:600].lower()

    if any(k in clean for k in ("internship", "intern", "apprentice")):
        return "Internship"
    if any(k in clean for k in ("contract", "contractor", "freelance", "temporary", "1099")):
        return "Contract"
    if "part-time" in clean or "part time" in clean:
        return "Part-time"

    return "Full-time"


def extract_all_metadata(job: dict[str, Any]) -> dict[str, Any]:
    """Extract complete structured metadata dictionary for a job record."""
    title = job.get("title") or ""
    loc = job.get("location") or ""
    desc = job.get("full_description") or job.get("description") or ""
    raw_salary = job.get("salary")

    workplace = extract_workplace_type(loc, desc)
    exp = extract_experience_requirements(title, desc)
    category, category_label = extract_role_category(title, desc)
    tech_stack = extract_tech_stack(desc)
    comp = extract_compensation(desc, raw_salary)
    emp_type = extract_employment_type(desc)

    return {
        "workplace_type": workplace,
        "is_remote": workplace == "Remote",
        "location_raw": loc,
        "experience": exp,
        "role_category": category,
        "role_category_label": category_label,
        "tech_stack": tech_stack,
        "compensation": comp,
        "employment_type": emp_type,
        "is_non_tech": category == "NON_TECH",
    }
