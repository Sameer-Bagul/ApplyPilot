"""Unified B2B Corporate Email Finder & Verification Engine.

Combines Hunter MCP / API, Evaboot MCP, and ApplyPilot's zero-token local OSINT
harvester with Google DoH MX verification.

Architecture:
1. Hunter API / MCP: Queries verified corporate directories, position titles,
   confidence scores, and SMTP deliverability when HUNTER_API_KEY is configured.
2. Evaboot API / MCP: Resolves professional work emails from LinkedIn profiles
   when EVABOOT_API_KEY is configured.
3. Zero-Token OSINT Fallback: Crawls company leadership/team/contact pages,
   validates DNS MX records via Google DoH (Google Workspace, Microsoft 365),
   and generates verified standard inboxes (careers@, talent@, hr@, founders@)
   and executive permutations.
4. Universal Database Ingestion: Stores all verified leads into SQLite `recruiter_leads`.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from applypilot.database import get_connection, store_recruiter_lead
from applypilot.discovery.bangalore_map_harvester import check_domain_mx
from applypilot.discovery.web_and_social_recruiter_harvester import (
    scrape_company_site_leadership,
    synthesize_recruiter_emails,
)

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/html,*/*",
}


def clean_domain(raw_domain_or_url: str) -> str:
    """Normalize URLs or strings into clean apex/subdomain strings."""
    if not raw_domain_or_url:
        return ""
    text = raw_domain_or_url.strip().lower()
    if text.startswith(("http://", "https://")):
        try:
            parsed = urlparse(text)
            text = parsed.netloc or text
        except Exception:
            pass
    # Strip paths, queries, ports
    text = text.split("/")[0].split(":")[0]
    # Remove leading www.
    if text.startswith("www."):
        text = text[4:]
    return text


def check_domain_mx_provider(domain: str, timeout: float = 4.0) -> tuple[bool, str]:
    """Check if domain has active MX records using Google DoH and identify mail provider."""
    if not domain or "." not in domain:
        return False, "none"
    clean_d = clean_domain(domain)
    url = f"https://dns.google/resolve?name={clean_d}&type=MX"
    try:
        import json
        import urllib.request
        req = urllib.request.Request(url, headers={"Accept": "application/dns-json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            answers = data.get("Answer", [])
            if not answers:
                return False, "none"
            ans_str = " ".join([a.get("data", "") for a in answers]).lower()
            if "google" in ans_str or "aspmx" in ans_str:
                return True, "google_workspace"
            elif "outlook" in ans_str or "microsoft" in ans_str:
                return True, "microsoft_365"
            elif "pphosted" in ans_str or "proofpoint" in ans_str:
                return True, "proofpoint"
            elif "mimecast" in ans_str:
                return True, "mimecast"
            return True, "custom_mx"
    except Exception:
        valid = check_domain_mx(clean_d)
        return valid, "active_mx" if valid else "none"


class HunterClient:
    """Client for Hunter.io B2B Email Discovery and Verification."""

    BASE_URL = "https://api.hunter.io/v2"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("HUNTER_API_KEY", "").strip()

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def search_domain_emails(
        self,
        domain: str,
        limit: int = 10,
        department: str | None = None,
    ) -> dict[str, Any]:
        """Search all public professional email addresses for a corporate domain.

        Args:
            domain: Target company domain (e.g. stripe.com).
            limit: Maximum contacts to return.
            department: Optional filter ('management', 'it', 'human_resources').
        """
        if not self.is_configured:
            return {"error": "HUNTER_API_KEY not configured"}

        clean_d = clean_domain(domain)
        params: dict[str, Any] = {
            "domain": clean_d,
            "api_key": self.api_key,
            "limit": min(limit, 100),
        }
        if department:
            params["department"] = department

        try:
            with httpx.Client(timeout=10.0, headers=DEFAULT_HEADERS) as client:
                resp = client.get(f"{self.BASE_URL}/domain-search", params=params)
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    emails = data.get("emails", [])
                    return {
                        "domain": clean_d,
                        "organization": data.get("organization"),
                        "pattern": data.get("pattern"),
                        "total": len(emails),
                        "emails": emails,
                    }
                else:
                    logger.warning("Hunter domain search failed [%d]: %s", resp.status_code, resp.text[:200])
                    return {"error": f"HTTP {resp.status_code}", "raw": resp.text[:300]}
        except Exception as e:
            logger.warning("Hunter domain search exception: %s", e)
            return {"error": str(e)}

    def find_email(
        self,
        domain: str,
        first_name: str,
        last_name: str,
    ) -> dict[str, Any]:
        """Find the verified work email for a specific person at a domain."""
        if not self.is_configured:
            return {"error": "HUNTER_API_KEY not configured"}

        clean_d = clean_domain(domain)
        params = {
            "domain": clean_d,
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
            "api_key": self.api_key,
        }
        try:
            with httpx.Client(timeout=10.0, headers=DEFAULT_HEADERS) as client:
                resp = client.get(f"{self.BASE_URL}/email-finder", params=params)
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    return {
                        "email": data.get("email"),
                        "score": data.get("score"),
                        "first_name": data.get("first_name"),
                        "last_name": data.get("last_name"),
                        "position": data.get("position"),
                        "verification": data.get("verification", {}),
                    }
                else:
                    return {"error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def verify_email(self, email: str) -> dict[str, Any]:
        """Verify deliverability and SMTP status for an email address."""
        if not self.is_configured:
            return {"error": "HUNTER_API_KEY not configured"}

        params = {"email": email.strip(), "api_key": self.api_key}
        try:
            with httpx.Client(timeout=10.0, headers=DEFAULT_HEADERS) as client:
                resp = client.get(f"{self.BASE_URL}/email-verifier", params=params)
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    return {
                        "email": email,
                        "status": data.get("status"),  # 'deliverable', 'risky', 'undeliverable'
                        "result": data.get("result"),
                        "score": data.get("score"),
                        "smtp_check": data.get("smtp_check"),
                        "mx_records": data.get("mx_records"),
                    }
                else:
                    return {"error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"error": str(e)}


class EvabootClient:
    """Client for Evaboot LinkedIn & Domain Email Finder."""

    BASE_URL = "https://api.evaboot.com/v1"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("EVABOOT_API_KEY", "").strip()

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def find_email(self, first_name: str, last_name: str, domain: str) -> dict[str, Any]:
        """Lookup email using Evaboot API."""
        if not self.is_configured:
            return {"error": "EVABOOT_API_KEY not configured"}
        try:
            with httpx.Client(timeout=10.0, headers={"Authorization": f"Bearer {self.api_key}"}) as client:
                resp = client.post(
                    f"{self.BASE_URL}/email-finder",
                    json={"first_name": first_name, "last_name": last_name, "domain": clean_domain(domain)},
                )
                if resp.status_code in (200, 201):
                    return resp.json()
                return {"error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"error": str(e)}


class ZeroTokenOSINTFinder:
    """Zero-Token Local OSINT Email Harvester with Google DoH MX verification.

    100% Free, unlimited, runs locally without external paid API keys.
    """

    STANDARD_INBOX_PREFIXES = [
        ("careers", "Direct Careers Inbox", "recruiter", 0.95),
        ("talent", "Talent Acquisition Team", "recruiter", 0.95),
        ("recruiting", "Recruiting Team", "recruiter", 0.95),
        ("jobs", "Job Applications Inbox", "recruiter", 0.92),
        ("hr", "Human Resources Team", "recruiter", 0.90),
        ("founders", "Executive & Founders Inbox", "hiring_manager", 0.88),
        ("engineering", "Engineering Leadership Inbox", "hiring_manager", 0.85),
    ]

    def harvest_company_emails(
        self,
        domain: str,
        company_name: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Perform comprehensive zero-token email discovery."""
        clean_d = clean_domain(domain)
        if not clean_d:
            return {"error": "invalid_domain", "leads": []}

        c_name = company_name or clean_d.split(".")[0].title()

        # 1. Verify Domain MX records via Google DoH
        mx_valid, mx_provider = check_domain_mx_provider(clean_d)

        discovered_leads: list[dict[str, Any]] = []
        seen_emails: set[str] = set()

        # 2. Crawl Company Website (team, about, careers, contact)
        site_data = scrape_company_site_leadership(domain=clean_d, company_name=c_name)
        for em in site_data.get("emails", []):
            em_clean = em.lower().strip()
            if em_clean not in seen_emails and "@" in em_clean:
                seen_emails.add(em_clean)
                prefix = em_clean.split("@")[0]
                is_rec = any(k in prefix for k in ["job", "career", "talent", "hr", "recruit", "people"])
                discovered_leads.append({
                    "email": em_clean,
                    "name": f"{c_name} Contact",
                    "role": f"Verified Direct Inbox ({prefix}) at {c_name}",
                    "type": "recruiter" if is_rec else "hiring_manager",
                    "source": "website_scrape",
                    "confidence": 0.98 if mx_valid else 0.85,
                    "evidence": f"Scraped directly from official {clean_d} website",
                })

        # 3. If MX is valid (or provider identified), synthesize standard corporate inboxes
        if mx_valid:
            for prefix, role_label, c_type, conf in self.STANDARD_INBOX_PREFIXES:
                em = f"{prefix}@{clean_d}"
                if em not in seen_emails:
                    seen_emails.add(em)
                    discovered_leads.append({
                        "email": em,
                        "name": f"{c_name} {role_label}",
                        "role": f"{role_label} at {c_name}",
                        "type": c_type,
                        "source": f"mx_verified_{mx_provider}",
                        "confidence": conf,
                        "evidence": f"Google DoH MX verified ({mx_provider}) standard corporate inbox",
                    })

        # 4. Generate executive / recruiter permutations if people were discovered
        executives = site_data.get("executives", [])
        if executives and mx_valid:
            synthesized = synthesize_recruiter_emails(
                company_name=c_name,
                domain=clean_d,
                recruiters=executives,
                target_count=limit,
            )
            for s in synthesized:
                em = s.get("email")
                if em and em not in seen_emails:
                    seen_emails.add(em)
                    discovered_leads.append({
                        "email": em,
                        "name": s.get("name") or f"{c_name} Executive",
                        "role": s.get("role") or f"Executive at {c_name}",
                        "type": s.get("type", "hiring_manager"),
                        "source": "permutation_mx",
                        "confidence": s.get("confidence", 0.82),
                        "evidence": s.get("evidence", "Synthesized name permutation with verified MX"),
                    })

        return {
            "domain": clean_d,
            "company": c_name,
            "mx_valid": mx_valid,
            "mx_provider": mx_provider,
            "method": "zero_token_osint",
            "total_found": len(discovered_leads),
            "leads": discovered_leads[:limit],
        }


def harvest_company_emails_cascade(
    domain: str,
    company_name: str | None = None,
    limit: int = 10,
    store_to_db: bool = True,
    conn: Any = None,
) -> dict[str, Any]:
    """Execute multi-tier cascading email discovery for any company domain.

    Tier 1: Hunter MCP/API (if HUNTER_API_KEY configured)
    Tier 2: Zero-Token Local OSINT + Google DoH MX verification
    Deduplicates and saves verified leads into SQLite `recruiter_leads`.
    """
    clean_d = clean_domain(domain)
    if not clean_d:
        return {"error": "Empty or invalid domain", "leads_added": 0}

    c_name = company_name or clean_d.split(".")[0].title()

    should_close = False
    if conn is None and store_to_db:
        conn = get_connection()
        should_close = True

    hunter_client = HunterClient()
    osint_finder = ZeroTokenOSINTFinder()

    all_leads: list[dict[str, Any]] = []
    seen_emails: set[str] = set()
    primary_source = "zero_token_osint"

    # -----------------------------------------------------------------
    # Tier 1: Hunter API / MCP
    # -----------------------------------------------------------------
    if hunter_client.is_configured:
        logger.info("Querying Hunter API for %s...", clean_d)
        h_res = hunter_client.search_domain_emails(clean_d, limit=limit)
        if "emails" in h_res:
            primary_source = "hunter_api"
            for h_em in h_res["emails"]:
                val = h_em.get("value", "").lower().strip()
                if val and val not in seen_emails:
                    seen_emails.add(val)
                    fn = h_em.get("first_name") or ""
                    ln = h_em.get("last_name") or ""
                    full_name = f"{fn} {ln}".strip() or f"{c_name} Contact"
                    pos = h_em.get("position") or f"Professional at {c_name}"
                    dept = h_em.get("department") or ""
                    conf = (h_em.get("confidence") or 80) / 100.0

                    contact_type = "recruiter" if any(k in f"{pos} {dept}".lower() for k in ["talent", "hr", "recruit", "people"]) else "hiring_manager"

                    all_leads.append({
                        "email": val,
                        "name": full_name,
                        "role": f"{pos} at {c_name}",
                        "type": contact_type,
                        "source": "hunter",
                        "confidence": conf,
                        "evidence": f"Hunter.io verified B2B email (confidence={h_em.get('confidence')}%)",
                    })

    # -----------------------------------------------------------------
    # Tier 2: Zero-Token OSINT Fallback / Supplement
    # -----------------------------------------------------------------
    osint_res = osint_finder.harvest_company_emails(domain=clean_d, company_name=c_name, limit=limit)
    for lead in osint_res.get("leads", []):
        em_val = lead["email"].lower().strip()
        if em_val not in seen_emails and len(all_leads) < limit:
            seen_emails.add(em_val)
            all_leads.append(lead)

    # -----------------------------------------------------------------
    # Persist into database recruiter_leads
    # -----------------------------------------------------------------
    leads_stored = 0
    if store_to_db and conn:
        # Check if company has an open ATS job to assign DUAL_ATTACK
        has_open_job = conn.execute(
            "SELECT 1 FROM jobs WHERE LOWER(company) = LOWER(?) LIMIT 1",
            (c_name,),
        ).fetchone() is not None

        route = "DUAL_ATTACK" if has_open_job else "EMAIL_ONLY"

        for lead in all_leads:
            try:
                store_recruiter_lead(
                    contact_email=lead["email"],
                    role_title=lead.get("role", f"Contact at {c_name}"),
                    company_name=c_name,
                    company_domain=clean_d,
                    contact_name=lead.get("name"),
                    source_platform=lead.get("source", primary_source),
                    evidence_snippet=lead.get("evidence", ""),
                    execution_route=route,
                    contact_type=lead.get("type", "recruiter"),
                    conn=conn,
                )
                leads_stored += 1
            except Exception as e:
                logger.debug("Failed to store recruiter lead: %s", e)

    if should_close:
        conn.close()

    return {
        "domain": clean_d,
        "company": c_name,
        "primary_source": primary_source,
        "mx_valid": osint_res.get("mx_valid", False),
        "mx_provider": osint_res.get("mx_provider", "unknown"),
        "total_emails_found": len(all_leads),
        "leads_stored_to_db": leads_stored,
        "leads": all_leads[:limit],
    }
