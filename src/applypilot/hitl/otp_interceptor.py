"""ATS Verification Code & Magic Link Interceptor.

Scans Gmail for 6-digit verification OTP codes and account activation magic links
sent during Workday, iCIMS, or Taleo account creation.
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any
import urllib.request
import urllib.parse

logger = logging.getLogger(__name__)

import os

GMAIL_MCP_DIR = Path(os.environ.get("GMAIL_MCP_DIR", str(Path.home() / ".gmail-mcp")))
CREDENTIALS_PATH = GMAIL_MCP_DIR / "credentials.json"

# Common OTP extraction regexes with required contextual proximity
_OTP_PATTERNS = [
    re.compile(r"(?i)\bverification\s*code\s*(?:is|:)?\s*(\d{6})\b"),
    re.compile(r"(?i)\bsecurity\s*code\s*(?:is|:)?\s*(\d{6})\b"),
    re.compile(r"(?i)\bone-time\s*pass(?:code|word)\s*(?:is|:)?\s*(\d{6})\b"),
    re.compile(r"(?i)\bOTP\s*(?:is|:)?\s*(\d{6})\b"),
    re.compile(r"(?i)\b(?:your\s+)?code\s*(?:is|:)?\s*(\d{6})\b"),
    re.compile(r"(?i)\bconfirm(?:ation)?\s*code\s*(?:is|:)?\s*(\d{6})\b"),
    re.compile(r"(?i)\b(\d{6})\b\s*(?:is your\s+)?(?:verification|security|one-time|login|auth)"),
]

# Magic link activation URL pattern
_MAGIC_LINK_PATTERN = re.compile(r"https?://[^\s\"'<>]+(?:verify|activate|token|confirm|auth)[^\s\"'<>]+")


def extract_otp_from_text(text: str) -> str | None:
    """Extract a 6-digit verification code from email text."""
    if not text:
        return None
    for pat in _OTP_PATTERNS:
        match = pat.search(text)
        if match:
            return match.group(1)
    return None


def extract_magic_link_from_text(text: str) -> str | None:
    """Extract an account activation or verification link from text."""
    if not text:
        return None
    match = _MAGIC_LINK_PATTERN.search(text)
    return match.group(0) if match else None


def fetch_ats_otp_code(company_domain: str = "",
                       sender_hint: str = "",
                       max_wait_seconds: int = 45,
                       poll_interval: int = 5) -> dict[str, Any]:
    """Poll Gmail for verification codes or magic links from ATS registration.

    Returns:
        {
            "otp_code": str | None,
            "magic_link": str | None,
            "sender": str | None,
        }
    """
    if not CREDENTIALS_PATH.exists():
        logger.debug("Gmail credentials not found. Returning empty OTP result.")
        return {"otp_code": None, "magic_link": None, "sender": None}

    try:
        creds = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
        token = creds.get("access_token")
        if not token:
            return {"otp_code": None, "magic_link": None, "sender": None}
    except Exception:
        return {"otp_code": None, "magic_link": None, "sender": None}

    # Query terms for search
    query_parts = ["is:unread", "newer_than:10m"]
    if company_domain:
        query_parts.append(f"({company_domain} OR workday OR icims OR verification)")
    elif sender_hint:
        query_parts.append(sender_hint)
    else:
        query_parts.append("(verification OR code OR activate OR confirm)")

    q_str = " ".join(query_parts)
    query_encoded = urllib.parse.quote(q_str)

    start_time = time.time()

    while (time.time() - start_time) < max_wait_seconds:
        try:
            url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages?q={query_encoded}&maxResults=5"
            req = urllib.request.Request(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )

            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                messages = data.get("messages", [])

            for msg_meta in messages:
                msg_id = msg_meta.get("id")
                # Fetch snippet
                detail_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}?format=snippet"
                detail_req = urllib.request.Request(
                    detail_url,
                    headers={"Authorization": f"Bearer {token}"},
                )
                with urllib.request.urlopen(detail_req, timeout=15) as d_resp:
                    detail = json.loads(d_resp.read().decode("utf-8"))
                    snippet = detail.get("snippet", "")

                otp = extract_otp_from_text(snippet)
                link = extract_magic_link_from_text(snippet)

                if otp or link:
                    logger.info("Found ATS auth code: %s (link: %s)", otp, link)
                    return {
                        "otp_code": otp,
                        "magic_link": link,
                        "message_id": msg_id,
                    }

        except Exception as e:
            logger.debug("Error querying Gmail for OTP: %s", e)

        time.sleep(poll_interval)

    return {"otp_code": None, "magic_link": None, "sender": None}


def wait_for_ats_otp(sender_domain: str | None = None, timeout_sec: int = 90) -> str | None:
    """Poll Gmail for a 6-digit verification code from an ATS domain."""
    res = fetch_ats_otp_code(
        company_domain=sender_domain or "",
        max_wait_seconds=timeout_sec,
        poll_interval=5,
    )
    return res.get("otp_code")
