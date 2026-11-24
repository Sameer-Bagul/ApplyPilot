"""Dynamic Email Pattern Deduction Engine.

Infers corporate email schemas (e.g. {first}.{last}, {f}{last}, {first})
from scraped web emails and observed personnel, applying deduced patterns
to discovered leadership and recruiter profiles.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

CANONICAL_PATTERNS = [
    "{first}.{last}",
    "{f}{last}",
    "{first}",
    "{first}_{last}",
    "{first}{l}",
    "{first}{last}",
    "{last}.{first}",
]

GENERIC_INBOX_PREFIXES = {
    "careers", "jobs", "talent", "hiring", "hr", "info", "support",
    "contact", "sales", "hello", "press", "media", "team", "billing",
    "founders", "admin", "help", "office", "marketing", "inquiries",
    "general", "security", "privacy", "legal", "compliance",
}


def clean_name_tokens(full_name: str) -> tuple[str, str]:
    """Extract clean lowercase first and last name tokens."""
    if not full_name:
        return "", ""
    parts = [re.sub(r"[^a-zA-Z]", "", p).lower() for p in full_name.split() if p.strip()]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[-1]


def render_email(pattern: str, full_name: str, domain: str) -> str:
    """Render an email using a specific pattern formula."""
    first, last = clean_name_tokens(full_name)
    clean_d = domain.lower().replace("www.", "").strip()
    if not first:
        return f"contact@{clean_d}"
    if not last:
        return f"{first}@{clean_d}"

    f = first[0]
    l = last[0]

    local = pattern.replace("{first}", first)
    local = local.replace("{last}", last)
    local = local.replace("{f}", f)
    local = local.replace("{l}", l)

    return f"{local}@{clean_d}"


def match_name_to_email_pattern(local_part: str, full_name: str) -> str | None:
    """Test if a local email username matches any canonical pattern for a given name."""
    first, last = clean_name_tokens(full_name)
    if not first:
        return None

    local = local_part.lower().strip()
    f = first[0]
    l = last[0] if last else ""

    if last:
        if local == f"{first}.{last}":
            return "{first}.{last}"
        if local == f"{f}{last}":
            return "{f}{last}"
        if local == f"{first}_{last}":
            return "{first}_{last}"
        if local == f"{first}{l}":
            return "{first}{l}"
        if local == f"{first}{last}":
            return "{first}{last}"
        if local == f"{last}.{first}":
            return "{last}.{first}"

    if local == first:
        return "{first}"

    return None


class EmailPatternEngine:
    """Deduces corporate email address formats and applies them to decision-makers."""

    def __init__(self, default_pattern: str = "{first}.{last}"):
        self.default_pattern = default_pattern

    def deduce_pattern(
        self,
        emails: list[str],
        sample_people: list[dict[str, Any]] | None = None,
        domain: str | None = None,
    ) -> dict[str, Any]:
        """Infer the most probable corporate email pattern for a domain.

        Args:
            emails: Raw observed email addresses (from scraping, press, or social).
            sample_people: Optional list of known company employees/executives with 'name'.
            domain: Target company domain to isolate corporate addresses.

        Returns:
            Dict containing deduced pattern, confidence (0.0 - 1.0), and evidence details.
        """
        clean_d = (domain or "").lower().replace("www.", "").strip()
        candidates: list[str] = []

        # Filter emails
        for em in set(emails or []):
            em_clean = em.lower().strip()
            if "@" not in em_clean:
                continue
            user, d = em_clean.split("@", 1)
            if clean_d and clean_d not in d:
                continue
            if user in GENERIC_INBOX_PREFIXES:
                continue
            candidates.append(user)

        people = sample_people or []
        pattern_votes: dict[str, float] = {p: 0.0 for p in CANONICAL_PATTERNS}
        evidence_matches: list[str] = []

        # Strategy 1: Match observed emails against known person names (Highest Confidence: 0.95)
        for user in candidates:
            for p in people:
                p_name = p.get("name", "")
                matched_pat = match_name_to_email_pattern(user, p_name)
                if matched_pat:
                    pattern_votes[matched_pat] += 5.0
                    evidence_matches.append(f"Confirmed match '{user}' for '{p_name}' ({matched_pat})")

        # Strategy 2: Structural syntax frequency of non-generic emails
        for user in candidates:
            if "." in user:
                parts = user.split(".")
                if len(parts) == 2 and len(parts[0]) > 1 and len(parts[1]) > 1:
                    pattern_votes["{first}.{last}"] += 1.0
                elif len(parts) == 2 and len(parts[0]) == 1 and len(parts[1]) > 1:
                    pattern_votes["{f}.{last}"] = pattern_votes.get("{f}.{last}", 0.0) + 1.0
            elif "_" in user:
                parts = user.split("_")
                if len(parts) == 2 and len(parts[0]) > 1 and len(parts[1]) > 1:
                    pattern_votes["{first}_{last}"] += 1.0
            elif len(user) >= 3:
                # Could be single name e.g. 'sameer' or 'asoin'
                pattern_votes["{first}"] += 0.4
                pattern_votes["{f}{last}"] += 0.4

        # Determine winning pattern
        best_pattern = self.default_pattern
        max_vote = 0.0
        for pat, vote in pattern_votes.items():
            if vote > max_vote:
                max_vote = vote
                best_pattern = pat

        if max_vote >= 5.0:
            confidence = 0.95
            evidence = "; ".join(evidence_matches[:2])
        elif max_vote >= 2.0:
            confidence = 0.85
            evidence = f"Deduced from {len(candidates)} non-generic observed email addresses"
        elif candidates:
            confidence = 0.72
            evidence = f"Deduced from structure of {candidates[0]}@{clean_d or 'company.com'}"
        else:
            confidence = 0.50
            evidence = f"No personal emails observed; default schema ({self.default_pattern})"

        return {
            "pattern": best_pattern,
            "confidence": round(confidence, 2),
            "evidence": evidence,
            "observed_count": len(candidates),
        }

    def apply_pattern_to_people(
        self,
        people: list[dict[str, Any]],
        domain: str,
        pattern: str | None = None,
        confidence: float | None = None,
    ) -> list[dict[str, Any]]:
        """Apply the deduced pattern to leadership profiles that lack verified emails."""
        chosen_pattern = pattern or self.default_pattern
        clean_d = domain.lower().replace("www.", "").strip()
        updated: list[dict[str, Any]] = []

        for p in people:
            p_copy = dict(p)
            name = p_copy.get("name", "")
            current_email = p_copy.get("email")

            # If person has no email or only a synthetic fallback, render with deduced pattern
            if not current_email or current_email.endswith("@connect.linkedin.com") or current_email.startswith("leadership."):
                synthesized = render_email(chosen_pattern, name, clean_d)
                p_copy["email"] = synthesized
                p_copy["email_pattern"] = chosen_pattern
                p_copy["email_pattern_confidence"] = confidence or 0.85

            updated.append(p_copy)

        return updated

