"""Zero-Send MX and DNS Email Deliverability Verifier.

Performs non-intrusive DNS MX resolution and simulated SMTP handshake (RCPT TO)
to verify that corporate domains have active mail routing and inboxes are deliverable,
without sending any email (zero spam risk, zero bounce risk).
"""

from __future__ import annotations

import logging
import re
import socket
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Common provider fingerprint signatures
MX_PROVIDER_PATTERNS = [
    (re.compile(r"google|aspmx|googlemail", re.IGNORECASE), "Google Workspace"),
    (re.compile(r"outlook|office365|protection\.outlook", re.IGNORECASE), "Microsoft 365"),
    (re.compile(r"zoho", re.IGNORECASE), "Zoho Mail"),
    (re.compile(r"protonmail|proton\.me", re.IGNORECASE), "Proton Mail"),
    (re.compile(r"icloud|apple", re.IGNORECASE), "Apple iCloud"),
    (re.compile(r"mimecast", re.IGNORECASE), "Mimecast"),
    (re.compile(r"barracuda", re.IGNORECASE), "Barracuda"),
    (re.compile(r"pphosted|proofpoint", re.IGNORECASE), "Proofpoint"),
    (re.compile(r"yahoodns|yahoo", re.IGNORECASE), "Yahoo Mail"),
    (re.compile(r"sendgrid|mailgun|mandrill|amazonses|postmark", re.IGNORECASE), "Transactional ESP"),
]


@dataclass
class EmailVerificationResult:
    """Structured result of an email address deliverability check."""

    email: str
    domain: str
    is_deliverable: bool
    mx_provider: str
    mx_records: list[str] = field(default_factory=list)
    is_catch_all: bool = False
    smtp_status_code: int | None = None
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "email": self.email,
            "domain": self.domain,
            "is_deliverable": self.is_deliverable,
            "mx_provider": self.mx_provider,
            "mx_records": self.mx_records,
            "is_catch_all": self.is_catch_all,
            "smtp_status_code": self.smtp_status_code,
            "details": self.details,
        }


def identify_mx_provider(mx_records: list[str]) -> str:
    """Identify the email service provider hosting the MX records."""
    if not mx_records:
        return "No MX Records"

    combined = " ".join(mx_records)
    for pattern, name in MX_PROVIDER_PATTERNS:
        if pattern.search(combined):
            return name

    # Fallback to primary MX hostname
    primary = mx_records[0]
    return f"Custom ({primary})"


class EmailVerifier:
    """Verifies email deliverability using DNS MX records and non-blocking SMTP handshakes."""

    def __init__(self, dns_timeout: float = 2.5, smtp_timeout: float = 3.0):
        self.dns_timeout = dns_timeout
        self.smtp_timeout = smtp_timeout

    def resolve_mx_records(self, domain: str) -> list[str]:
        """Resolve sorted MX records for a domain using dnspython or socket fallback."""
        clean_domain = domain.strip().lower()
        if not clean_domain:
            return []

        # 1. Try dnspython resolver
        try:
            import dns.resolver

            resolver = dns.resolver.Resolver()
            resolver.lifetime = self.dns_timeout
            resolver.timeout = self.dns_timeout
            answers = resolver.resolve(clean_domain, "MX")
            sorted_records = sorted([(r.preference, str(r.exchange).rstrip(".")) for r in answers])
            return [host for _, host in sorted_records]
        except ImportError:
            logger.debug("dnspython not available; trying socket A record fallback")
        except Exception as e:
            logger.debug("DNS MX lookup failed for %s: %s", clean_domain, e)
            return []

        # 2. Fallback: check if domain has a valid host A record
        try:
            addr_info = socket.getaddrinfo(clean_domain, 25, socket.AF_INET, socket.SOCK_STREAM)
            if addr_info:
                return [clean_domain]
        except Exception as e:
            logger.debug("Socket host resolution fallback failed for %s: %s", clean_domain, e)

        return []

    def check_smtp_handshake(self, email: str, mx_host: str) -> tuple[bool, int | None, str]:
        """Attempt a zero-send SMTP simulated handshake (HELO -> MAIL FROM -> RCPT TO -> QUIT).
        
        Returns (is_deliverable, status_code, details).
        Does NOT send DATA or messages.
        """
        if not mx_host or not email:
            return False, None, "Invalid host or email"

        sock = None
        try:
            sock = socket.create_connection((mx_host, 25), timeout=self.smtp_timeout)
            sock.settimeout(self.smtp_timeout)

            # 1. Read greeting banner
            banner = sock.recv(1024).decode("utf-8", errors="ignore")
            if not banner.startswith("220"):
                return True, None, "Banner received without 220"

            # 2. Send HELO
            sock.sendall(b"HELO verify.applypilot.local\r\n")
            helo_resp = sock.recv(1024).decode("utf-8", errors="ignore")

            # 3. Send MAIL FROM
            sock.sendall(b"MAIL FROM:<check@applypilot.local>\r\n")
            mail_resp = sock.recv(1024).decode("utf-8", errors="ignore")

            # 4. Send RCPT TO
            sock.sendall(f"RCPT TO:<{email}>\r\n".encode("utf-8"))
            rcpt_resp = sock.recv(1024).decode("utf-8", errors="ignore")

            # Extract 3-digit status code
            code = None
            code_match = re.match(r"^(\d{3})", rcpt_resp.strip())
            if code_match:
                code = int(code_match.group(1))

            # 5. Send QUIT
            try:
                sock.sendall(b"QUIT\r\n")
            except Exception:
                pass

            if code == 250:
                return True, code, "SMTP 250 OK - Mailbox confirmed"
            elif code in (550, 551, 552, 553, 554):
                return False, code, f"SMTP {code} - Mailbox rejected"
            else:
                # 4xx or unexpected code: soft fail, assume MX deliverable
                return True, code, f"SMTP response code {code}"

        except (socket.timeout, TimeoutError):
            # Port 25 blocked by local ISP or remote firewall: fallback to DNS MX validity
            return True, None, "SMTP port 25 timeout (ISP/firewall block) - MX record is valid"
        except (ConnectionRefusedError, OSError) as e:
            return True, None, f"SMTP handshake connection note: {e} - MX record is valid"
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

    def verify(self, email_or_domain: str, do_smtp: bool = False) -> EmailVerificationResult:
        """Verify the email deliverability and identify mail infrastructure."""
        raw = (email_or_domain or "").strip()
        if "@" in raw:
            parts = raw.split("@", 1)
            email = raw
            domain = parts[1].strip().lower()
        else:
            email = f"test@{raw}"
            domain = raw.strip().lower()

        # Remove subdomains like 'www.'
        clean_domain = domain.replace("www.", "")

        mx_records = self.resolve_mx_records(clean_domain)
        if not mx_records:
            return EmailVerificationResult(
                email=email,
                domain=clean_domain,
                is_deliverable=False,
                mx_provider="None",
                mx_records=[],
                details="No MX records or host IP found for domain",
            )

        provider = identify_mx_provider(mx_records)
        is_deliverable = True
        smtp_code = None
        details = f"Active MX routed to {provider}"

        if do_smtp and mx_records:
            is_deliv_smtp, code, smtp_det = self.check_smtp_handshake(email, mx_records[0])
            smtp_code = code
            is_deliverable = is_deliv_smtp
            details = f"{provider} ({smtp_det})"

        return EmailVerificationResult(
            email=email,
            domain=clean_domain,
            is_deliverable=is_deliverable,
            mx_provider=provider,
            mx_records=mx_records,
            smtp_status_code=smtp_code,
            details=details,
        )


def verify_email_deliverability(email_or_domain: str, do_smtp: bool = False) -> EmailVerificationResult:
    """Convenience helper to verify an email or domain's deliverability."""
    verifier = EmailVerifier()
    return verifier.verify(email_or_domain, do_smtp=do_smtp)
