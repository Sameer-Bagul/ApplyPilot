"""Stack-Aware Dynamic Portfolio Matcher.

Analyzes a target company's detected tech stack and engineering keywords,
then matches and ranks Sameer's flagship GitHub projects to highlight the
most relevant codebases and architectures in cold outreach.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PortfolioProject:
    """A flagship engineering project available for targeted showcase."""

    id: str
    name: str
    pitch_bullet: str
    github_url: str
    tech_keywords: list[str]
    primary_domain: str  # e.g., 'agentic_ai', 'fullstack_web', 'backend_systems'


SAMEER_PROJECTS: list[PortfolioProject] = [
    PortfolioProject(
        id="athena",
        name="Athena (Autonomous 3D Companion)",
        pitch_bullet="Athena: Autonomous 3D desktop companion with 60 FPS Three.js rendering and LangGraph multi-agent routing",
        github_url="https://github.com/Sameer-Bagul",
        tech_keywords=[
            "python",
            "langgraph",
            "langchain",
            "agent",
            "agentic",
            "ai",
            "llm",
            "fastapi",
            "pytorch",
            "three.js",
            "threejs",
            "3d",
            "companion",
            "voice",
            "websocket",
            "composio",
            "anthropic",
            "gemini",
        ],
        primary_domain="agentic_ai",
    ),
    PortfolioProject(
        id="applypilot",
        name="ApplyPilot (Autonomous Browser Engine)",
        pitch_bullet="ApplyPilot: High-throughput autonomous browser engine with zero-token SQLite caching and Next.js 16 App Router",
        github_url="https://github.com/Sameer-Bagul",
        tech_keywords=[
            "react",
            "typescript",
            "javascript",
            "next.js",
            "nextjs",
            "playwright",
            "headless",
            "browser",
            "scraping",
            "crawler",
            "sqlite",
            "fullstack",
            "frontend",
            "automation",
            "tailwind",
            "mdx",
            "node",
        ],
        primary_domain="fullstack_web",
    ),
    PortfolioProject(
        id="distributed_rag",
        name="Distributed Systems & Hybrid RAG Engine",
        pitch_bullet="Production B2B lead generation & hybrid RAG pipelines across Python, Postgres, and vector retrieval",
        github_url="https://github.com/Sameer-Bagul",
        tech_keywords=[
            "backend",
            "database",
            "distributed",
            "postgresql",
            "postgres",
            "redis",
            "rag",
            "vector",
            "docker",
            "microservices",
            "architecture",
            "elasticsearch",
            "sql",
            "api",
            "grpc",
        ],
        primary_domain="backend_systems",
    ),
]


def match_portfolio_projects(
    company_tech_stack: list[str] | None,
    max_projects: int = 2,
) -> list[PortfolioProject]:
    """Rank and select the best matching portfolio projects for a given company tech stack.
    
    Scores each project by the number of keyword intersections with the company tech stack.
    Guarantees at least 1 project is returned even with an empty tech stack.
    """
    normalized_stack = {s.lower().strip() for s in (company_tech_stack or []) if s}

    scored: list[tuple[int, PortfolioProject]] = []
    for proj in SAMEER_PROJECTS:
        score = 0
        for kw in proj.tech_keywords:
            if kw in normalized_stack:
                score += 3
            elif any(kw in s or s in kw for s in normalized_stack):
                score += 1
        scored.append((score, proj))

    # Sort descending by score
    scored.sort(key=lambda x: x[0], reverse=True)

    selected = [p for _, p in scored[:max_projects]]
    return selected or [SAMEER_PROJECTS[0], SAMEER_PROJECTS[1]]


def format_portfolio_pitch(company_tech_stack: list[str] | None, max_projects: int = 2) -> str:
    """Format a customized bullet-point text block for inclusion in email drafts."""
    matched = match_portfolio_projects(company_tech_stack, max_projects=max_projects)
    bullets = "\n".join(f"- {p.pitch_bullet}" for p in matched)
    return bullets
