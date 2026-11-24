"""Batch Gemini Email Draft Generator for High-Conversion Personalized Outreach.

Batches 10-15 company-lead pairs into a single prompt for Gemini 2.0 Flash.
Generates tailored, persona-aware, and non-generic cold emails in structured JSON.

Persona Angles:
1. 'hr': Direct role match, notice period (Immediate-15 days), core skills summary, resume PDF.
2. 'founder': High-impact technical pitch, company stack citation, flagship projects (Athena/ApplyPilot), GitHub proof.
3. 'engineer': Technical peer tone citing specific open source tools or shared engineering challenges.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from applypilot import config
from applypilot.llm import get_client

logger = logging.getLogger("applypilot.batch_generator")


def _load_candidate_context() -> dict[str, Any]:
    """Load core facts, projects, and experiences from candidate profile."""
    profile_path = getattr(config, "PROFILE_PATH", None)
    if profile_path and profile_path.exists():
        try:
            return json.loads(profile_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "name": "Sameer Bagul",
        "email": "sameerbagul2004@gmail.com",
        "current_title": "AI Engineer | Full Stack",
        "current_company": "Revcloud",
        "years_of_experience": 2.5,
        "notice_period": "Immediate to 15 Days",
        "skills": ["Python", "FastAPI", "React", "TypeScript", "LangGraph", "Docker", "Playwright", "LLM", "PostgreSQL"],
        "urls": {
            "github": "https://github.com/Sameer-Bagul",
            "linkedin": "https://www.linkedin.com/in/sameer-bagul",
            "portfolio": "https://sameerbagul.com",
        },
    }


def _build_batch_prompt(batch: list[dict[str, Any]], candidate: dict[str, Any]) -> str:
    """Construct a dense, structured JSON prompt containing all leads in the batch."""
    candidate_summary = {
        "name": candidate.get("name") or "Sameer Bagul",
        "email": candidate.get("email") or "sameerbagul2004@gmail.com",
        "current_title": candidate.get("current_title") or "AI Engineer | Full Stack",
        "years_of_experience": candidate.get("years_of_experience", 2.5),
        "notice_period": candidate.get("notice_period", "Immediate to 15 Days"),
        "primary_skills": candidate.get("skills", [])[:15],
        "flagship_projects": [
            "Athena: Autonomous 3D desktop AI companion with Three.js/VRM 60 FPS rendering, LangGraph multi-provider routing, Python Whisper & MCP tool execution.",
            "ApplyPilot: Autonomous job application & web form automation system with Playwright and zero-token learning engine.",
            "Revcloud AI Systems: Production B2B lead generation & revenue funnel intelligence with LangGraph, hybrid RAG, and FastAPI.",
        ],
        "github": candidate.get("urls", {}).get("github", "https://github.com/Sameer-Bagul"),
        "linkedin": candidate.get("urls", {}).get("linkedin", "https://www.linkedin.com/in/sameer-bagul"),
    }

    leads_payload = []
    for lead in batch:
        intel = lead.get("company_intel", {})
        open_roles = intel.get("open_roles", [])
        matched_role = open_roles[0].get("title") if open_roles else (lead.get("role_title") or "Software Engineer")

        leads_payload.append({
            "lead_id": lead["lead_id"],
            "contact_name": lead.get("contact_name") or "Hiring Team",
            "contact_email": lead["contact_email"],
            "persona": lead.get("persona") or "founder",
            "company_name": lead.get("company_name") or "the company",
            "company_domain": lead.get("company_domain") or intel.get("official_domain", ""),
            "matched_role": matched_role,
            "company_summary": intel.get("wikipedia_summary", "")[:300],
            "company_tech_stack": intel.get("tech_stack", [])[:8],
            "ai_focus_tags": intel.get("ai_focus_tags", []),
            "execution_route": lead.get("execution_route", "EMAIL_ONLY"),
        })

    prompt = f"""You are an elite, highly targeted cold email writer for a senior software engineer.
Generate bespoke, personalized, high-converting cold email drafts for each of the {len(batch)} recipients below.

CANDIDATE FACTS (STRICT GROUND TRUTH - NEVER HALLUCINATE OUTSIDE THESE FACTS):
{json.dumps(candidate_summary, indent=2)}

TARGET LEADS & COMPANY INTELLIGENCE:
{json.dumps(leads_payload, indent=2)}

STRICT WRITING RULES PER PERSONA:
1. For 'hr' / Recruiter:
   - Mention the specific open position or technical area right away.
   - State immediate availability/notice period ({candidate_summary['notice_period']}).
   - Concise bullet list of 3 relevant skills matching their company.
   - Reference the attached resume PDF.
2. For 'founder' / CTO:
   - Punchy, high-energy, peer-to-peer engineering tone.
   - Specifically cite what their company builds or their tech stack ({' ,'.join(batch[0].get('company_intel', {}).get('tech_stack', [])[:3]) if batch else 'relevant stack'}).
   - Highlight 1 relevant flagship project (e.g. Athena, ApplyPilot, or Revcloud) with concrete architectural details.
   - Include GitHub link ({candidate_summary['github']}) and ask for a quick 10-minute technical chat.
3. For 'engineer' / Tech Lead:
   - Technical curiosity, acknowledging their open-source or product architecture.
   - Ask for engineering perspective or a direct internal referral.
4. General Rules:
   - Keep emails concise (under 130 words).
   - If execution_route is 'DUAL_ATTACK', include a brief note: "I have also submitted my application via your careers portal."
   - Never sound like an AI template. Use clean paragraphs, natural phrasing, and direct subject lines.

OUTPUT FORMAT:
Respond ONLY with a valid JSON object matching this exact schema:
{{
  "drafts": [
    {{
      "lead_id": "<exact lead_id>",
      "subject": "<punchy subject line>",
      "body_text": "<plain text email body including salutation and sign-off>",
      "body_html": "<clean HTML email body styled with standard typography>",
      "cta": "<call to action sentence>",
      "match_reason": "<1-sentence summary of why this lead was targeted>"
    }}
  ]
}}
"""
    return prompt


def _generate_fallback_draft(lead: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """Deterministic fallback draft when LLM API is unavailable."""
    name = candidate.get("name") or "Sameer Bagul"
    cand_email = candidate.get("email") or "sameerbagul2004@gmail.com"
    github = candidate.get("urls", {}).get("github", "https://github.com/Sameer-Bagul")
    linkedin = candidate.get("urls", {}).get("linkedin", "https://www.linkedin.com/in/sameer-bagul")

    c_name = lead.get("company_name") or "your team"
    role = lead.get("role_title") or "Software Engineer"
    recipient = lead.get("contact_name") or "Hiring Team"
    salutation = f"Hi {recipient.split()[0]}," if recipient and recipient != "Hiring Team" else "Hi Hiring Team,"
    persona = lead.get("persona") or "founder"

    intel = lead.get("company_intel", {})
    stack = ", ".join(intel.get("tech_stack", [])[:3]) or "Python & React"

    if persona == "hr":
        subject = f"Application: {role} — {name}"
        body_text = f"""{salutation}

I came across {c_name}'s open engineering opportunities and wanted to share my background directly for the {role} role.

I bring 2.5 years of experience building production AI services, autonomous agent pipelines, and full-stack architectures. My background directly aligns with {stack}.

Key highlights:
- Hands-on experience with FastAPI, Python, React, and LangGraph agentic workflows
- Immediate availability (Notice Period: {candidate.get('notice_period', 'Immediate to 15 Days')})
- GitHub: {github}
- LinkedIn: {linkedin}

I have attached my tailored resume (PDF) for your consideration. I'd welcome the chance to speak with your team.

Best regards,
{name}
{cand_email}
"""
    else:
        subject = f"{name} // {c_name} engineering & {role}"
        body_text = f"""{salutation}

I've been following {c_name}'s work and wanted to reach out directly regarding engineering and product execution.

I am an AI & Full-Stack Engineer specializing in autonomous systems, distributed APIs, and production LLM architectures. Given your work around {stack}, my background aligns well with your technical goals.

A few recent flagship projects:
- Athena: Autonomous 3D desktop companion with 60 FPS Three.js rendering and LangGraph routing
- ApplyPilot: High-throughput autonomous browser engine with zero-token SQLite caching
- Production B2B lead generation & hybrid RAG pipelines across Python and React

My code and repositories are available at {github}. I'd love to grab 10 minutes to discuss how I can contribute to {c_name}.

Best regards,
{name}
{cand_email}
"""

    body_html = f"<div style='font-family: -apple-system, sans-serif; line-height: 1.6; color: #1f2937;'>{body_text.replace(chr(10), '<br>')}</div>"

    return {
        "lead_id": lead["lead_id"],
        "subject": subject,
        "body_text": body_text.strip(),
        "body_html": body_html,
        "cta": "I would welcome the opportunity to connect.",
        "match_reason": f"Fallback draft matching {persona} persona and {c_name} tech stack",
    }


class BatchDraftGenerator:
    """Generates persona-tailored cold email drafts in batches of 10-15 using Gemini."""

    def __init__(self, batch_size: int = 12) -> None:
        self.batch_size = max(1, min(20, batch_size))
        self.candidate = _load_candidate_context()

    def generate_drafts_for_leads(self, leads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Slice leads into micro-batches and generate structured drafts."""
        if not leads:
            return []

        all_drafts: list[dict[str, Any]] = []

        # Process in micro-batches
        for i in range(0, len(leads), self.batch_size):
            batch = leads[i : i + self.batch_size]
            logger.info("Generating batch drafts for %d leads (batch %d)...", len(batch), (i // self.batch_size) + 1)

            drafts = self._call_gemini_batch(batch)
            all_drafts.extend(drafts)

        return all_drafts

    def _call_gemini_batch(self, batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Dispatch a single structured prompt to Gemini, with fallback to template generation."""
        prompt = _build_batch_prompt(batch, self.candidate)
        lead_id_map = {lead["lead_id"]: lead for lead in batch}

        try:
            client = get_client(quality=False)  # Uses fast model (Gemini 2.0 Flash)
            response_text = client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=4096,
            )

            # Strip markdown formatting if present
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```[a-zA-Z]*\n", "", cleaned)
                cleaned = re.sub(r"\n```$", "", cleaned)

            data = json.loads(cleaned)
            drafts = data.get("drafts", [])

            # Validate each draft matches a lead in the batch
            valid_drafts: list[dict[str, Any]] = []
            seen_ids: set[str] = set()

            for d in drafts:
                lid = d.get("lead_id")
                if lid in lead_id_map and lid not in seen_ids:
                    seen_ids.add(lid)
                    valid_drafts.append(d)

            # Check if any lead in the batch was missed; fallback for missed leads
            for lead in batch:
                if lead["lead_id"] not in seen_ids:
                    logger.warning("Lead %s missing from LLM output; using fallback draft", lead["lead_id"])
                    valid_drafts.append(_generate_fallback_draft(lead, self.candidate))

            return valid_drafts

        except Exception as e:
            logger.warning("Gemini batch draft call failed (%s); generating deterministic fallback drafts", e)
            return [_generate_fallback_draft(lead, self.candidate) for lead in batch]

