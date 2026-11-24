"""Lead Ranker & Persona Classifier for High-Conversion Cold Outreach.

Ranks queued recruiter leads using multi-signal alignment:
1. Open Job Match: Active relevant job listing at company (highest priority).
2. Tech Stack Match: Direct overlap with candidate's AI & software engineering skills.
3. Target Persona: Classifies recipient as 'hr', 'founder', or 'engineer'.
4. Deliverability Safeguards: Filters out invalid syntax, missing domains, or contacted leads.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from typing import Any

from applypilot import config
from applypilot.database import get_connection, get_recruiter_leads
from applypilot.discovery.company_intel_service import CompanyIntelService

logger = logging.getLogger("applypilot.lead_ranker")

# Regex keywords for persona classification
RECRUITER_KEYWORDS = re.compile(
    r"\b(hr|talent|recruiter|recruiting|people|talent acquisition|sourcer|staffing|careers)\b",
    re.IGNORECASE,
)
FOUNDER_KEYWORDS = re.compile(
    r"\b(founder|co-founder|cofounder|ceo|cto|chief executive|chief technology|managing director|partner|owner)\b",
    re.IGNORECASE,
)
ENGINEER_KEYWORDS = re.compile(
    r"\b(engineers?|engineering|developer|architect|tech lead|vp of engineering|vp engineering|director of engineering|head of engineering|devops|sre)\b",
    re.IGNORECASE,
)


def classify_recipient_persona(
    contact_name: str | None = "",
    contact_email: str | None = "",
    role_title: str | None = "",
    evidence_snippet: str | None = "",
) -> str:
    """Classify recipient into one of: 'hr', 'founder', or 'engineer'.
    
    Default fallback is 'founder' for early-stage social posts, or 'hr' for careers inboxes.
    """
    c_name = (contact_name or "").strip()
    c_email = (contact_email or "").strip()
    c_title = (role_title or "").strip()
    c_evidence = (evidence_snippet or "").strip()

    combined_title = f"{c_title} {c_evidence}".lower()
    email_local = c_email.split("@")[0].lower() if "@" in c_email else ""

    # 1. Check exact email prefix conventions
    if any(p in email_local for p in ["founder", "cto", "ceo", "co-founder"]):
        return "founder"
    if any(p in email_local for p in ["hr", "careers", "jobs", "recruiting", "talent", "people", "ta"]):
        return "hr"

    # 2. Check role title and evidence text
    if FOUNDER_KEYWORDS.search(combined_title):
        return "founder"
    if RECRUITER_KEYWORDS.search(combined_title):
        return "hr"
    if ENGINEER_KEYWORDS.search(combined_title):
        return "engineer"

    # 3. Fallback based on name or generic lead
    if any(w in c_name.lower() for w in ["recruiter", "talent", "hr"]):
        return "hr"
    if any(w in c_name.lower() for w in ["founder", "cto"]):
        return "founder"

    return "founder"  # Default high-impact target


def compute_lead_priority(
    lead: dict[str, Any],
    company_intel: dict[str, Any],
    candidate_skills: list[str] | set[str] | None = None,
) -> int:
    """Calculate multi-signal priority score (0 to 100) for a lead.
    
    Breakdown:
    - Active Matching Job: +40 pts (Fit Score >= 7 or relevant title)
    - Tech Stack Alignment: up to +35 pts (Matching technologies & AI focus)
    - Target Persona (Founder/HR): +15 pts
    - Domain & Email Quality: +10 pts
    """
    contact_email = (lead.get("contact_email") or "").strip().lower()
    if not contact_email or "@" not in contact_email:
        return 0

    score = 0
    skills_set = {s.lower() for s in (candidate_skills or ["python", "react", "fastapi", "docker", "llm", "ai", "langchain", "playwright"])}

    # 1. Active Open Job Matching (+40 max)
    open_roles = company_intel.get("open_roles", [])
    has_role_match = False
    for r in open_roles:
        r_title = (r.get("title") or "").lower()
        r_fit = r.get("fit_score") or 0
        if r_fit >= 7 or any(k in r_title for k in ["ai", "full stack", "software", "backend", "python", "agent", "llm"]):
            has_role_match = True
            break

    if has_role_match:
        score += 40
    elif lead.get("role_title") and any(k in lead["role_title"].lower() for k in ["ai", "full stack", "software", "backend", "engineer"]):
        score += 30  # Explicit role from social post

    # 2. Tech Stack & AI Domain Alignment (+35 max)
    company_stack = {t.lower() for t in company_intel.get("tech_stack", [])}
    ai_tags = company_intel.get("ai_focus_tags", [])
    
    matched_skills = skills_set.intersection(company_stack)
    if len(matched_skills) >= 3:
        score += 25
    elif len(matched_skills) >= 1:
        score += 15

    if ai_tags:
        score += 10  # Operates in candidate's primary domain (AI/LLM)

    # 3. Recipient Persona Intent (+15 max)
    persona = lead.get("persona") or classify_recipient_persona(
        lead.get("contact_name", ""),
        contact_email,
        lead.get("role_title", ""),
        lead.get("evidence_snippet", ""),
    )
    if persona in ("founder", "hr"):
        score += 15
    else:
        score += 10

    # 4. Domain & Email Verification (+10 max)
    domain = lead.get("company_domain") or company_intel.get("official_domain", "")
    if domain and "." in domain:
        score += 10

    # Bonus: DUAL_ATTACK opportunity (+5)
    if lead.get("execution_route") == "DUAL_ATTACK":
        score += 5

    return min(100, score)


class LeadRanker:
    """Ranks and selects top queued leads using company intel and persona classification."""

    def __init__(
        self,
        conn: sqlite3.Connection | None = None,
        workspace: int = 11,
        headless: bool = False,
        live_scrape: bool = False,
    ) -> None:
        self.conn = conn
        self.workspace = workspace
        self.headless = headless
        self.live_scrape = live_scrape

    def select_daily_top_picks(
        self,
        limit: int = 20,
        min_score: int = 60,
        force_research: bool = False,
        live_scrape: bool | None = None,
    ) -> list[dict[str, Any]]:
        """Rank all queued leads, research missing company intel, and return top picks."""
        conn = self.conn or get_connection()
        should_crawl = self.live_scrape if live_scrape is None else live_scrape
        intel_service = CompanyIntelService(
            conn=conn,
            workspace=self.workspace,
            headless=self.headless,
            live_scrape=should_crawl,
        )

        # 1. Fetch queued leads
        queued = get_recruiter_leads(status="queued", limit=None, conn=conn)
        if not queued:
            logger.info("No queued recruiter leads found in database.")
            return []

        # 2. Load candidate skills from profile
        candidate_skills: list[str] = []
        try:
            profile_path = getattr(config, "PROFILE_PATH", None)
            if profile_path and profile_path.exists():
                import json
                pdata = json.loads(profile_path.read_text(encoding="utf-8"))
                candidate_skills = pdata.get("skills") or pdata.get("skills_boundary", {}).get("languages", [])
        except Exception:
            pass
        if not candidate_skills:
            candidate_skills = ["Python", "React", "FastAPI", "TypeScript", "LangGraph", "Docker", "LLM", "Playwright"]

        # 3. Pre-fetch company intel for unique companies in the batch (fast OSINT, no live crawl yet)
        company_map = intel_service.enrich_batch_for_leads(
            queued,
            force_refresh=force_research,
            live_scrape=False,
        )

        # 4. Score each lead and update DB
        ranked_leads: list[tuple[int, str, dict[str, Any], dict[str, Any]]] = []

        for lead in queued:
            c_name = lead.get("company_name") or ""
            domain = lead.get("company_domain") or ""
            key = (domain or c_name).strip().lower()

            intel = company_map.get(key) or intel_service.get_or_research(c_name, domain=domain, force_refresh=force_research, live_scrape=False)
            persona = classify_recipient_persona(
                lead.get("contact_name", ""),
                lead.get("contact_email", ""),
                lead.get("role_title", ""),
                lead.get("evidence_snippet", ""),
            )
            lead["persona"] = persona

            score = compute_lead_priority(lead, intel, candidate_skills)
            lead["priority_score"] = score

            # Update DB with computed score and persona
            try:
                conn.execute(
                    """
                    UPDATE recruiter_leads 
                    SET priority_score = ?, persona = ? 
                    WHERE lead_id = ?
                    """,
                    (score, persona, lead["lead_id"]),
                )
            except Exception as e:
                logger.debug("Failed updating lead score for %s: %s", lead["lead_id"], e)

            if score >= min_score:
                ranked_leads.append((score, persona, lead, intel))

        conn.commit()

        # 5. Sort by priority score DESC
        ranked_leads.sort(key=lambda x: x[0], reverse=True)

        # 6. If live_scrape is requested, execute live headed crawl ONLY on top candidate companies!
        top_candidates = list(ranked_leads[:limit])
        if should_crawl and top_candidates:
            crawled_keys: set[str] = set()
            for idx, (score, persona, lead, intel) in enumerate(top_candidates):
                c_name = lead.get("company_name") or ""
                domain = lead.get("company_domain") or ""
                key = (domain or c_name).strip().lower()

                if key not in crawled_keys and (not intel.get("open_roles") or force_research):
                    crawled_keys.add(key)
                    logger.info("🎯 [Top Pick Live Crawl] Investigating top pick company '%s' on Workspace %d...", c_name, self.workspace)
                    fresh_intel = intel_service.get_or_research(
                        c_name, domain=domain, force_refresh=True, live_scrape=True
                    )
                    company_map[key] = fresh_intel
                    intel.update(fresh_intel)
                    new_score = compute_lead_priority(lead, fresh_intel, candidate_skills)
                    lead["priority_score"] = new_score
                    top_candidates[idx] = (new_score, persona, lead, fresh_intel)

            top_candidates.sort(key=lambda x: x[0], reverse=True)

        selected: list[dict[str, Any]] = []
        for score, persona, lead, intel in top_candidates:
            lead_copy = dict(lead)
            lead_copy["company_intel"] = intel
            selected.append(lead_copy)

        logger.info(
            "Selected %d top-pick leads (out of %d queued, min_score=%d)",
            len(selected),
            len(queued),
            min_score,
        )
        return selected
