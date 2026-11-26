"""Unit tests for the Zero-Send MX and DNS Email Deliverability Verifier."""

from unittest.mock import MagicMock, patch

import pytest
from applypilot.verification.email_verifier import (
    EmailVerifier,
    identify_mx_provider,
    verify_email_deliverability,
)


def test_identify_mx_provider():
    assert identify_mx_provider(["aspmx.l.google.com", "alt1.aspmx.l.google.com"]) == "Google Workspace"
    assert identify_mx_provider(["acme-com.mail.protection.outlook.com"]) == "Microsoft 365"
    assert identify_mx_provider(["mx.zoho.com"]) == "Zoho Mail"
    assert identify_mx_provider(["mail.protonmail.ch"]) == "Proton Mail"
    assert identify_mx_provider(["mail.acmecorp.net"]) == "Custom (mail.acmecorp.net)"
    assert identify_mx_provider([]) == "No MX Records"


def test_resolve_mx_records_mocked():
    verifier = EmailVerifier()
    with patch("dns.resolver.Resolver.resolve") as mock_resolve:
        mock_item1 = MagicMock()
        mock_item1.preference = 10
        mock_item1.exchange = "alt.aspmx.l.google.com."

        mock_item2 = MagicMock()
        mock_item2.preference = 1
        mock_item2.exchange = "aspmx.l.google.com."

        mock_resolve.return_value = [mock_item1, mock_item2]

        records = verifier.resolve_mx_records("example.com")
        assert len(records) == 2
        assert records[0] == "aspmx.l.google.com"
        assert records[1] == "alt.aspmx.l.google.com"


def test_verify_deliverable_email():
    verifier = EmailVerifier()
    with patch.object(verifier, "resolve_mx_records", return_value=["aspmx.l.google.com"]):
        res = verifier.verify("founder@startup.io")
        assert res.is_deliverable is True
        assert res.mx_provider == "Google Workspace"
        assert res.domain == "startup.io"


def test_verify_undeliverable_domain():
    verifier = EmailVerifier()
    with patch.object(verifier, "resolve_mx_records", return_value=[]):
        res = verifier.verify("fake@doesnotexistdomain12345.xyz")
        assert res.is_deliverable is False
        assert res.mx_provider == "None"


def test_smtp_handshake_simulation():
    verifier = EmailVerifier()
    with patch("socket.create_connection") as mock_conn:
        mock_sock = MagicMock()
        mock_sock.recv.side_effect = [
            b"220 mail.example.com ESMTP\r\n",
            b"250 Hello\r\n",
            b"250 Sender OK\r\n",
            b"250 Recipient OK\r\n",
        ]
        mock_conn.return_value = mock_sock

        deliverable, code, details = verifier.check_smtp_handshake("user@example.com", "mail.example.com")
        assert deliverable is True
        assert code == 250
        assert "confirmed" in details.lower()

