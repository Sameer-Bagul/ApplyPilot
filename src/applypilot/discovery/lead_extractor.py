"""Zero-Token Regex & Entity Classifier for social hiring posts.

Extracts published emails, ATS links, evidence snippets, and classifies
opportunities into execution routes (EMAIL_ONLY, PORTAL_ONLY, DUAL_ATTACK)
with zero LLM token consumption.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

# Blacklisted local-parts / generic support addresses
_GENERIC_EMAIL_PREFIXES = {
    "noreply",
    "no-reply",
    "donotreply",
    "do-not-reply",
    "support",
    "help",
    "billing",
    "abuse",
    "privacy",
    "security",
    "legal",
    "terms",
    "admin",
    "postmaster",
    "mailer-daemon",
    "mailerdaemon",
    "root",
    "feedback",
    "contact",
}

_GENERIC_DOMAINS = {
    "example.com",
    "test.com",
    "domain.com",
    "sample.com",
    "reddit.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "threads.net",
    "facebook.com",
    "instagram.com",
    "youtube.com",
}

# Known ATS portal domains
KNOWN_ATS_DOMAINS = [
    "boards.greenhouse.io",
    "job-boards.greenhouse.io",
    "greenhouse.io",
    "jobs.lever.co",
    "lever.co",
    "jobs.ashbyhq.com",
    "ashbyhq.com",
    "myworkdayjobs.com",
    "workday.com",
    "icims.com",
    "smartrecruiters.com",
    "bamboohr.com",
    "applytojob.com",
    "workable.com",
    "rippling-ats.com",
    "jobs.jobvite.com",
    "jobvite.com",
    "recruitee.com",
    "breezy.hr",
    "freshteam.com",
    "join.com",
    "pinpointhq.com",
    "dayforcehcm.com",
]

_EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", re.IGNORECASE
)

# Obfuscated patterns like user [at] company [dot] com, user(at)company(dot)com
_OBFUSCATED_PATTERNS = [
    re.compile(r"([a-zA-Z0-9_.+-]+)\s*\[at\]\s*([a-zA-Z0-9-]+)\s*\[dot\]\s*([a-zA-Z0-9-.]+)", re.IGNORECASE),
    re.compile(r"([a-zA-Z0-9_.+-]+)\s*\(at\)\s*([a-zA-Z0-9-]+)\s*\(dot\)\s*([a-zA-Z0-9-.]+)", re.IGNORECASE),
    re.compile(r"([a-zA-Z0-9_.+-]+)\s*@\s*([a-zA-Z0-9-]+)\s*\.\s*([a-zA-Z0-9-.]+)", re.IGNORECASE),
    re.compile(r"([a-zA-Z0-9_.+-]+)\s+at\s+([a-zA-Z0-9-]+)\s+dot\s+([a-zA-Z0-9-.]+)", re.IGNORECASE),
]

_URL_REGEX = re.compile(
    r"https?://[^\s<>\"'()]+", re.IGNORECASE
)


def extract_emails(text: str) -> list[str]:
    """Extract and de-obfuscate valid HR/recruiter/founder emails from text."""
    if not text:
        return []

    candidates: set[str] = set()

    # 1. Standard emails
    for m in _EMAIL_REGEX.finditer(text):
        email = m.group(0).rstrip(".,;:!?)").lower()
        candidates.add(email)

    # 2. Obfuscated emails
    for pattern in _OBFUSCATED_PATTERNS:
        for m in pattern.finditer(text):
            user = m.group(1).strip()
            domain = m.group(2).strip()
            tld = m.group(3).rstrip(".,;:!?) ").strip()
            clean_email = f"{user}@{domain}.{tld}".lower()
            candidates.add(clean_email)

    # 3. mailto: links
    for m in re.finditer(r"mailto:([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", text, re.IGNORECASE):
        candidates.add(m.group(1).lower())

    valid_emails: list[str] = []
    for email in candidates:
        if "@" not in email:
            continue
        local, domain = email.split("@", 1)
        if local in _GENERIC_EMAIL_PREFIXES:
            continue
        if domain in _GENERIC_DOMAINS:
            continue
        if len(local) < 2 or len(domain) < 4 or "." not in domain:
            continue
        valid_emails.append(email)

    return sorted(valid_emails)


def extract_ats_urls(text: str) -> list[str]:
    """Extract known ATS application and career URLs from text."""
    if not text:
        return []

    found = []
    for match in _URL_REGEX.finditer(text):
        url = match.group(0).rstrip(".,;:!?)")
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if any(ats in domain for ats in KNOWN_ATS_DOMAINS):
            found.append(url)
    return list(dict.fromkeys(found))


def extract_all_urls(text: str) -> list[str]:
    """Extract all web URLs from text."""
    if not text:
        return []
    return [m.group(0).rstrip(".,;:!?)") for m in _URL_REGEX.finditer(text)]


def extract_evidence_snippet(text: str, target: str, max_chars: int = 240) -> str:
    """Extract a 1-2 sentence verbatim snippet surrounding the target keyword/email."""
    if not text or not target:
        return ""

    idx = text.lower().find(target.lower())
    if idx == -1:
        return text[:max_chars].strip()

    # Find approximate sentence boundary before and after
    start = max(0, idx - 120)
    end = min(len(text), idx + len(target) + 120)

    # Clean boundaries up to sentence or space
    snippet = text[start:end].replace("\n", " ").strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


def classify_contact_type(email: str, context_text: str = "") -> str:
    """Classify the contact email into founder, recruiter, hiring_manager, or careers_inbox."""
    local = email.split("@")[0].lower()
    text = (context_text + " " + local).lower()

    if any(k in local for k in ("careers", "jobs", "hiring", "join", "apply", "team")):
        return "careers_inbox"

    if any(k in text for k in ("founder", "co-founder", "cofounder", "ceo", "cto", "coo", "partner")):
        return "founder"

    if any(k in text for k in ("engineering manager", "hiring manager", "lead engineer", "vp engineering", "head of")):
        return "hiring_manager"

    if any(k in text for k in ("recruiter", "talent", "recruiting", "ta", "people", "hr", "human resources")):
        return "recruiter"

    return "recruiter"


def classify_execution_route(has_email: bool, has_portal_url: bool) -> str:
    """Determine execution route based on presence of direct email and/or portal URL."""
    if has_email and has_portal_url:
        return "DUAL_ATTACK"
    if has_email:
        return "EMAIL_ONLY"
    if has_portal_url:
        return "PORTAL_ONLY"
    return "UNKNOWN"


def parse_social_post(
    post_title: str,
    post_text: str,
    source_url: str = "",
    platform: str = "reddit",
) -> dict[str, Any]:
    """Parse a social post into structured lead and routing information."""
    combined_text = f"{post_title}\n\n{post_text}"
    emails = extract_emails(combined_text)
    ats_urls = extract_ats_urls(combined_text)
    all_urls = extract_all_urls(combined_text)

    has_email = len(emails) > 0
    has_ats = len(ats_urls) > 0
    route = classify_execution_route(has_email, has_ats)

    primary_email = emails[0] if emails else None
    primary_ats_url = ats_urls[0] if ats_urls else None

    # Determine contact type and evidence snippet
    contact_type = classify_contact_type(primary_email, combined_text) if primary_email else "unknown"
    target_needle = primary_email or primary_ats_url or post_title
    evidence = extract_evidence_snippet(combined_text, target_needle)

    # Heuristic company name extraction from title (e.g. "[Hiring] Acme Corp is looking for...")
    company_name = None
    title_clean = re.sub(r"\[.*?\]|\(.*?\)", "", post_title).strip()
    match = re.search(r"^(.*?)(?:\s+is\s+hiring|\s+is\s+looking|\s+hiring\s+|\s+seeking\s+|:)", title_clean, re.IGNORECASE)
    if match and len(match.group(1).split()) <= 4:
        company_name = match.group(1).strip()

    return {
        "emails": emails,
        "primary_email": primary_email,
        "contact_type": contact_type,
        "ats_urls": ats_urls,
        "primary_ats_url": primary_ats_url,
        "all_urls": all_urls,
        "execution_route": route,
        "evidence_snippet": evidence,
        "company_name": company_name,
        "source_post_url": source_url,
        "source_platform": platform,
    }
