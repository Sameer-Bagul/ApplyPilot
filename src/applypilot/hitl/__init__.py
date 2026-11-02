"""Human-In-The-Loop (HITL) module for asynchronous email escalation and state recovery.

Contains:
- Form state checkpointing and cookie vault
- Outbound email notifier for batched questions
- Inbound email reply parser and permanent knowledge promotion
- ATS OTP verification code and magic link interceptor
"""

from applypilot.hitl.checkpoint import (
    serialize_form_checkpoint,
    save_browser_session_cookies,
    load_browser_session_cookies,
    replay_checkpoint_playwright,
)
from applypilot.hitl.email_notifier import (
    format_hitl_email_subject,
    format_hitl_email_body,
    send_gmail_api,
    dispatch_hitl_email_and_park,
    park_and_notify_user,
)
from applypilot.hitl.email_reply_parser import (
    strip_email_quoted_headers,
    parse_reply_answers,
    resolve_answer_for_question,
    process_hitl_ticket_reply,
    sync_email_hitl_replies,
    poll_hitl_replies,
)
from applypilot.hitl.otp_interceptor import (
    extract_otp_from_text,
    extract_magic_link_from_text,
    fetch_ats_otp_code,
    wait_for_ats_otp,
)

__all__ = [
    "serialize_form_checkpoint",
    "save_browser_session_cookies",
    "load_browser_session_cookies",
    "replay_checkpoint_playwright",
    "format_hitl_email_subject",
    "format_hitl_email_body",
    "send_gmail_api",
    "dispatch_hitl_email_and_park",
    "park_and_notify_user",
    "strip_email_quoted_headers",
    "parse_reply_answers",
    "resolve_answer_for_question",
    "process_hitl_ticket_reply",
    "sync_email_hitl_replies",
    "poll_hitl_replies",
    "extract_otp_from_text",
    "extract_magic_link_from_text",
    "fetch_ats_otp_code",
    "wait_for_ats_otp",
]
