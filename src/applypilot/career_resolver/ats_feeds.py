"""Direct public ATS JSON board pollers (11 ATS Platforms).

Facade over applypilot.discovery.ats_direct_feeds.
"""

from __future__ import annotations

from applypilot.discovery.ats_direct_feeds import (
    poll_ashby_board,
    poll_bamboohr_board,
    poll_board,
    poll_breezy_board,
    poll_greenhouse_board,
    poll_lever_board,
    poll_personio_board,
    poll_recruitee_board,
    poll_smartrecruiters_board,
    poll_teamtailor_board,
    poll_watchlist,
    poll_workable_board,
    poll_workday_board,
)

__all__ = [
    "poll_greenhouse_board",
    "poll_lever_board",
    "poll_ashby_board",
    "poll_workday_board",
    "poll_workable_board",
    "poll_smartrecruiters_board",
    "poll_bamboohr_board",
    "poll_recruitee_board",
    "poll_teamtailor_board",
    "poll_breezy_board",
    "poll_personio_board",
    "poll_board",
    "poll_watchlist",
]
