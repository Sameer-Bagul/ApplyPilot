"""Pre-compiled, high-throughput regular expression registry.

Pre-compiling all regex patterns at module load time avoids thousands of
expensive re.compile() cycles inside tight discovery and extraction loops.
"""

from __future__ import annotations

import re

# Standard and RFC 5322 compatible email pattern
EMAIL_COMPILED_PATTERN = re.compile(
    r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9]{2,}\b",
    re.IGNORECASE,
)

# Obfuscated email patterns commonly found in social hiring posts
OBFUSCATED_AT_PATTERN = re.compile(
    r"\s*(?:\[at\]|\(at\)|\[AT\]|\(AT\)|<at>|{\s*at\s*}|\s+at\s+)\s*",
    re.IGNORECASE,
)

OBFUSCATED_DOT_PATTERN = re.compile(
    r"\s*(?:\[dot\]|\(dot\)|\[DOT\]|\(DOT\)|<dot>|{\s*dot\s*}|\s+dot\s+)\s*",
    re.IGNORECASE,
)

# Phone number patterns
PHONE_COMPILED_PATTERN = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
)

# Standard URL pattern
URL_COMPILED_PATTERN = re.compile(
    r"https?://[^\s<>\"'{}|\\^`\[\]]+",
    re.IGNORECASE,
)

# HTML script LD+JSON block pattern
LD_JSON_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)

# HTML tag stripping pattern
HTML_TAG_RE = re.compile(r"<[^>]+>")

# Known enterprise Applicant Tracking System domain signatures
KNOWN_ATS_DOMAINS = (
    "boards.greenhouse.io",
    "job-boards.greenhouse.io",
    "jobs.lever.co",
    "jobs.ashbyhq.com",
    "myworkdayjobs.com",
    "apply.workable.com",
    "careers.smartrecruiters.com",
    "bamboohr.com/careers",
    "breezy.hr",
    "recruitee.com",
    "rippling-ats.com",
    "gem.com",
    "pinpointhq.com",
    "teamtailor.com",
    "icims.com",
)

ATS_DOMAIN_PATTERNS = {
    "greenhouse": re.compile(r"boards\.greenhouse\.io/([a-zA-Z0-9_\-]+)", re.IGNORECASE),
    "greenhouse_embed": re.compile(r"[?&]for=([a-zA-Z0-9_\-]+)", re.IGNORECASE),
    "lever": re.compile(r"jobs\.lever\.co/([a-zA-Z0-9_\-]+)", re.IGNORECASE),
    "ashby": re.compile(r"jobs\.ashbyhq\.com/([a-zA-Z0-9_\-]+)", re.IGNORECASE),
    "workable": re.compile(r"apply\.workable\.com/([a-zA-Z0-9_\-]+)", re.IGNORECASE),
    "smartrecruiters": re.compile(r"careers\.smartrecruiters\.com/([a-zA-Z0-9_\-]+)", re.IGNORECASE),
    "bamboohr": re.compile(r"([a-zA-Z0-9_\-]+)\.bamboohr\.com", re.IGNORECASE),
}
