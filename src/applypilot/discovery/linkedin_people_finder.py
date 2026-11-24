"""Non-login LinkedIn Profile & Leadership Finder.

Discovers public LinkedIn profiles, member IDs, full names, and roles
for company founders, tech leaders, and recruiters using 100% non-login public OSINT:
1. Y Combinator Public Directory (Fast-path for YC companies & founders)
2. Local Database Recruiter Leads & VIP Watchlist
3. Public Web & Directory Discovery (DDGS / Public OSINT snippets)
4. Automated Personalized LinkedIn Connection Note Generator (< 300 chars)
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sqlite3
import urllib.parse
import urllib.request
from typing import Any

from applypilot import config
from applypilot.database import get_connection, store_recruiter_lead, save_company_intel, get_company_intel

logger = logging.getLogger("applypilot.linkedin_finder")

LINKEDIN_URL_PATTERN = re.compile(
    r"https?://(?:[a-zA-Z0-9-]+\.)?linkedin\.com/in/(?P<id>[a-zA-Z0-9_-]+)/?",
    re.IGNORECASE,
)

FOUNDER_KEYWORDS = re.compile(
    r"\b(founder|co-founder|cofounder|ceo|cto|managing director|partner|owner)\b",
    re.IGNORECASE,
)
ENGINEER_KEYWORDS = re.compile(
    r"\b(engineering|tech lead|architect|head of engineering|vp of engineering|devops|software)\b",
    re.IGNORECASE,
)
RECRUITER_KEYWORDS = re.compile(
    r"\b(recruiter|recruiting|talent|people|hr|sourcer)\b",
    re.IGNORECASE,
)


def extract_linkedin_id(url: str | None) -> str | None:
    """Extract username/slug ID from a LinkedIn profile URL."""
    if not url:
        return None
    match = LINKEDIN_URL_PATTERN.search(url)
    if match:
        return match.group("id")
    return None


def classify_persona_from_role(role: str | None) -> str:
    """Classify role string into founder, engineer, or hr."""
    r = (role or "").lower()
    if FOUNDER_KEYWORDS.search(r):
        return "founder"
    if RECRUITER_KEYWORDS.search(r):
        return "hr"
    if ENGINEER_KEYWORDS.search(r):
        return "engineer"
    return "founder"


def generate_linkedin_connection_note(
    person_name: str,
    role: str,
    company: str,
    candidate_skills: list[str] | None = None,
) -> str:
    """Generate a personalized LinkedIn connection request note under 300 characters."""
    first_name = (person_name.split()[0] if person_name else "there").strip()
    skills = candidate_skills or ["Python", "React", "AI", "FastAPI"]
    skill_str = f"{skills[0]}/{skills[1]}" if len(skills) >= 2 else skills[0]

    persona = classify_persona_from_role(role)
    if persona == "founder":
        note = f"Hi {first_name}, really impressed by what {company} is building. I'm a full-stack & AI engineer ({skill_str}) and would love to connect and follow your journey as you scale!"
    elif persona == "hr":
        note = f"Hi {first_name}, noticed your talent focus at {company}. I'm an engineer specializing in {skill_str} looking for impactful roles. Would love to connect and stay in touch!"
    else:
        note = f"Hi {first_name}, saw your engineering leadership at {company}. Great technical work! As a fellow engineer ({skill_str}), I'd love to connect and follow your team's updates."

    if len(note) > 295:
        note = note[:290] + "..."
    return note


class LinkedInPeopleFinder:
    """Finds leadership and recruiter LinkedIn profiles without requiring a LinkedIn login."""

    def __init__(self, conn: sqlite3.Connection | None = None) -> None:
        self.conn = conn

    def find_people_for_company(
        self,
        company_name: str,
        domain: str | None = None,
        candidate_skills: list[str] | None = None,
        max_people: int = 3,
    ) -> list[dict[str, Any]]:
        """Run non-login OSINT to discover key company personnel with LinkedIn profiles."""
        c_name = (company_name or "").strip()
        c_domain = (domain or "").strip().lower()
        if not c_name and not c_domain:
            return []

        conn = self.conn or get_connection()
        discovered: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        # Step 0: Check company_intel 30-day cache for previously discovered key_people_json
        try:
            cached_intel = get_company_intel(c_domain or c_name.lower(), conn=conn)
            if cached_intel and cached_intel.get("key_people_json"):
                kp = cached_intel["key_people_json"]
                if isinstance(kp, str):
                    try:
                        kp = json.loads(kp)
                    except Exception:
                        kp = []
                if isinstance(kp, list) and kp:
                    logger.info("   ├─ [LinkedIn Cache] Reusing %d cached people from company_intel for %s", len(kp), c_name)
                    return kp[:max_people]
        except Exception as e:
            logger.debug("Company intel people lookup notice: %s", e)

        # Step 1: Check existing local database for previously harvested LinkedIn profiles
        try:
            rows = conn.execute(
                """
                SELECT contact_name, contact_linkedin_url, role_title, persona, linkedin_connection_note
                FROM recruiter_leads
                WHERE (LOWER(company_name) = LOWER(?) OR (? != '' AND LOWER(company_domain) = LOWER(?)))
                  AND contact_linkedin_url IS NOT NULL AND contact_linkedin_url != ''
                LIMIT ?
                """,
                (c_name, c_domain, c_domain, max_people),
            ).fetchall()
            for r in rows:
                url = r["contact_linkedin_url"]
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    li_id = extract_linkedin_id(url)
                    discovered.append({
                        "name": r["contact_name"] or "Leadership Lead",
                        "role": r["role_title"] or "Executive",
                        "persona": r["persona"] or "founder",
                        "linkedin_url": url,
                        "linkedin_id": li_id,
                        "connection_note": r["linkedin_connection_note"] or generate_linkedin_connection_note(r["contact_name"], r["role_title"], c_name, candidate_skills),
                        "source": "database_cache",
                    })
            if discovered:
                logger.info("   ├─ [LinkedIn DB Cache] Matched %d verified profiles for %s", len(discovered), c_name)
                return discovered[:max_people]
        except Exception as e:
            logger.debug("Local leads LinkedIn lookup error: %s", e)

        # Step 2: Y Combinator Public Directory Fast-Path
        yc_people = self._probe_yc_directory(c_name, c_domain, candidate_skills)
        for p in yc_people:
            if p["linkedin_url"] not in seen_urls:
                seen_urls.add(p["linkedin_url"])
                discovered.append(p)

        if len(discovered) >= max_people:
            self._persist_people_to_leads(discovered[:max_people], c_name, c_domain, conn)
            return discovered[:max_people]

        # Step 3: Public Web OSINT via DuckDuckGo / Directory snippets
        web_people = self._probe_web_directory_snippets(c_name, c_domain, candidate_skills)
        for p in web_people:
            if p["linkedin_url"] not in seen_urls:
                seen_urls.add(p["linkedin_url"])
                discovered.append(p)

        results = discovered[:max_people]
        if results:
            self._persist_people_to_leads(results, c_name, c_domain, conn)

        return results

    def _probe_yc_directory(
        self,
        company_name: str,
        domain: str,
        candidate_skills: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Scrape founder profiles from Y Combinator directory if the startup is in YC."""
        slugs = []
        if domain:
            slugs.append(domain.split(".")[0].lower())
        slugs.append(re.sub(r"[^a-zA-Z0-9]", "", company_name).lower())

        people: list[dict[str, Any]] = []
        for s in set(slugs):
            yc_url = f"https://www.ycombinator.com/companies/{s}"
            try:
                # Fast HEAD probe to verify existence
                req = urllib.request.Request(yc_url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status != 200:
                        continue
                    html_content = resp.read().decode("utf-8", errors="ignore")

                # Extract founder URLs: /founders/12345-first-last
                founder_links = re.findall(r'href=["\'](/founders/\d+-[^"\']+)["\']', html_content)
                if not founder_links:
                    continue

                for f_rel in set(founder_links[:3]):
                    f_url = f"https://www.ycombinator.com{f_rel}"
                    try:
                        f_req = urllib.request.Request(f_url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"})
                        with urllib.request.urlopen(f_req, timeout=5) as f_resp:
                            f_html = f_resp.read().decode("utf-8", errors="ignore")

                        # Extract name from <h1> or URL slug (avoiding generic "Y Combinator" <title>)
                        slug_name = f_rel.split("-", 1)[1].replace("-", " ").title() if "-" in f_rel else "Founder"
                        h1_match = re.search(r"<h1[^>]*>([^<]+)</h1>", f_html)
                        clean_name = h1_match.group(1).strip() if h1_match else None
                        if not clean_name or clean_name.lower() in ("y combinator", "yc", "founder"):
                            title_match = re.search(r"<title>([^<|]+)", f_html)
                            t_val = title_match.group(1).strip() if title_match else ""
                            if t_val and t_val.lower() not in ("y combinator", "yc"):
                                clean_name = t_val
                            else:
                                clean_name = slug_name

                        # Extract LinkedIn profile URL
                        li_matches = re.findall(r'href=["\'](https://[^\s"\']*linkedin\.com/in/[^\s"\']+)["\']', f_html)
                        for li in li_matches:
                            clean_li = li.split("?")[0].rstrip("/")
                            li_id = extract_linkedin_id(clean_li)
                            if li_id and "y-combinator" not in li_id.lower():
                                note = generate_linkedin_connection_note(clean_name, "Founder / CEO", company_name, candidate_skills)
                                people.append({
                                    "name": clean_name,
                                    "role": "Founder / CEO",
                                    "persona": "founder",
                                    "linkedin_url": clean_li,
                                    "linkedin_id": li_id,
                                    "connection_note": note,
                                    "source": "ycombinator_directory",
                                })
                                break
                    except Exception as fe:
                        logger.debug("Failed fetching YC founder page %s: %s", f_url, fe)
            except Exception:
                continue

        return people

    def _probe_web_directory_snippets(
        self,
        company_name: str,
        domain: str,
        candidate_skills: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Search public startup databases and directories for founder and tech lead names."""
        people: list[dict[str, Any]] = []
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                query = f'"{company_name}" founder CEO'
                hits = list(ddgs.text(query, max_results=4))
                for h in hits:
                    body = h.get("body", "")
                    title = h.get("title", "")
                    text = f"{title} {body}"
                    # Pattern matching for founders
                    # e.g. "Mohammed Roshan is the Co-Founder and CEO of GoSats"
                    match = re.search(r"([A-Z][a-z]+ [A-Z][a-z]+)\s+(?:is|was)\s+(?:the\s+)?(?:Co-Founder|Founder|CEO|CTO)", text)
                    if match:
                        f_name = match.group(1).strip()
                        # Avoid company name false matches
                        if company_name.lower() not in f_name.lower():
                            # Query specifically for this person's LinkedIn profile
                            p_query = f'"{f_name}" "{company_name}" linkedin'
                            p_hits = list(ddgs.text(p_query, max_results=3))
                            for ph in p_hits:
                                ph_url = ph.get("href", "")
                                if "linkedin.com/in/" in ph_url:
                                    clean_li = ph_url.split("?")[0].rstrip("/")
                                    li_id = extract_linkedin_id(clean_li)
                                    if li_id:
                                        note = generate_linkedin_connection_note(f_name, "Founder / CEO", company_name, candidate_skills)
                                        people.append({
                                            "name": f_name,
                                            "role": "Founder / CEO",
                                            "persona": "founder",
                                            "linkedin_url": clean_li,
                                            "linkedin_id": li_id,
                                            "connection_note": note,
                                            "source": "web_dorking",
                                        })
                                        break
                            if people:
                                break
        except Exception as e:
            logger.debug("Web directory snippet probe notice: %s", e)

        return people

    def _persist_people_to_leads(
        self,
        people: list[dict[str, Any]],
        company_name: str,
        domain: str,
        conn: sqlite3.Connection,
    ) -> None:
        """Save discovered people into SQLite recruiter_leads and company_intel tables."""
        for p in people:
            u = p.get("linkedin_url")
            if not u:
                continue
            name = p.get("name", "Leadership Lead")
            role = p.get("role", "Executive")
            persona = p.get("persona", "founder")
            note = p.get("connection_note", "")

            # Synthetic contact email placeholder if not known
            slug_domain = domain or f"{re.sub(r'[^a-zA-Z0-9]', '', company_name).lower()}.com"
            synth_email = f"{name.lower().replace(' ', '.')}@{slug_domain}"

            try:
                store_recruiter_lead(
                    contact_email=synth_email,
                    role_title=f"{role} at {company_name}",
                    company_name=company_name,
                    contact_name=name,
                    contact_linkedin_url=u,
                    contact_type=persona,
                    persona=persona,
                    source_platform=p.get("source", "linkedin_osint"),
                    evidence_snippet=f"Discovered via non-login LinkedIn OSINT for {company_name}.",
                    linkedin_connection_note=note,
                    execution_route="DUAL_ATTACK",
                    conn=conn,
                )
            except Exception as e:
                logger.debug("Failed upserting LinkedIn recruiter lead: %s", e)

        # Update company_intel key_people_json
        try:
            intel = get_company_intel(domain or company_name.lower(), conn=conn) or {}
            intel["company_name"] = company_name
            intel["official_domain"] = domain
            intel["key_people_json"] = people
            save_company_intel(intel, conn=conn)
        except Exception as e:
            logger.debug("Failed saving key people to company_intel: %s", e)


def find_company_people_sync(
    company_name: str,
    domain: str | None = None,
    candidate_skills: list[str] | None = None,
    max_people: int = 3,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """Synchronous convenience entry point for LinkedIn people finder."""
    finder = LinkedInPeopleFinder(conn=conn)
    return finder.find_people_for_company(
        company_name=company_name,
        domain=domain,
        candidate_skills=candidate_skills,
        max_people=max_people,
    )
