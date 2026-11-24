"""Unit tests for the Stack-Aware Dynamic Portfolio Matcher."""

from applypilot.outreach.portfolio_matcher import (
    format_portfolio_pitch,
    match_portfolio_projects,
)


def test_match_ai_agent_stack():
    stack = ["Python", "LangGraph", "FastAPI", "AI"]
    matched = match_portfolio_projects(stack, max_projects=1)
    assert len(matched) == 1
    assert matched[0].id == "athena"


def test_match_fullstack_web_stack():
    stack = ["React", "TypeScript", "Next.js", "MDX"]
    matched = match_portfolio_projects(stack, max_projects=1)
    assert len(matched) == 1
    assert matched[0].id == "applypilot"


def test_match_backend_database_stack():
    stack = ["PostgreSQL", "Redis", "Distributed", "Microservices"]
    matched = match_portfolio_projects(stack, max_projects=1)
    assert len(matched) == 1
    assert matched[0].id == "distributed_rag"


def test_format_portfolio_pitch_fallback():
    pitch = format_portfolio_pitch([])
    assert "Athena" in pitch
    assert "ApplyPilot" in pitch
