"""Part 2A: Automated HR & Founder Cold Mailer package."""

from applypilot.outreach.mailer import (
    compose_cold_email,
    create_gmail_draft,
    extract_special_instructions,
    find_resume_pdf,
    run_hr_outreach,
)

__all__ = [
    "compose_cold_email",
    "create_gmail_draft",
    "extract_special_instructions",
    "find_resume_pdf",
    "run_hr_outreach",
]
