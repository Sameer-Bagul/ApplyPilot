"""Levergreen & ATS Seed Importer for ApplyPilot.

Ingests high-signal company career board tokens from Levergreen (adgramigna/job-board-scraper),
JobHive, and curated ATS registries (Greenhouse, Lever, Ashby, Workable, SmartRecruiters).

Populates `career_watchlist` with verified ATS slugs and triggers keyless, zero-token
job ingestion via `applypilot.discovery.ats_direct_feeds`.
"""

from __future__ import annotations

import csv
import io
import json
import logging
from typing import Any

import httpx

from applypilot.database import (
    get_connection,
    store_jobs,
    upsert_career_watchlist,
)
from applypilot.discovery.ats_direct_feeds import poll_board

logger = logging.getLogger("applypilot.levergreen_importer")

# Curated seed database of high-growth global & Indian tech startups using major ATS platforms
CURATED_ATS_SEEDS: list[dict[str, str]] = [
    # Ashby AI / Modern Startups
    {"name": "Mistral AI", "domain": "mistral.ai", "ats": "ashby", "token": "mistral", "sector": "AI"},
    {"name": "Perplexity AI", "domain": "perplexity.ai", "ats": "ashby", "token": "perplexity", "sector": "AI"},
    {"name": "Linear", "domain": "linear.app", "ats": "ashby", "token": "linear", "sector": "SaaS"},
    {"name": "Ramp", "domain": "ramp.com", "ats": "ashby", "token": "ramp", "sector": "Fintech"},
    {"name": "Vercel", "domain": "vercel.com", "ats": "ashby", "token": "vercel", "sector": "DevTools"},
    {"name": "Supabase", "domain": "supabase.com", "ats": "ashby", "token": "supabase", "sector": "DevTools"},
    {"name": "Cursor (Anysphere)", "domain": "cursor.com", "ats": "ashby", "token": "anysphere", "sector": "AI"},
    {"name": "Together AI", "domain": "together.ai", "ats": "ashby", "token": "togetherai", "sector": "AI"},
    {"name": "Resend", "domain": "resend.com", "ats": "ashby", "token": "resend", "sector": "DevTools"},
    {"name": "LangChain", "domain": "langchain.com", "ats": "ashby", "token": "langchain", "sector": "AI"},
    {"name": "Cohere", "domain": "cohere.com", "ats": "ashby", "token": "cohere", "sector": "AI"},
    {"name": "Scale AI", "domain": "scale.com", "ats": "ashby", "token": "scaleai", "sector": "AI"},
    {"name": "Sierra", "domain": "sierra.ai", "ats": "ashby", "token": "sierra", "sector": "AI"},
    {"name": "Harvey", "domain": "harvey.ai", "ats": "ashby", "token": "harvey", "sector": "AI/Legal"},
    {"name": "ElevenLabs", "domain": "elevenlabs.io", "ats": "ashby", "token": "elevenlabs", "sector": "AI/Audio"},
    {"name": "Postman", "domain": "postman.com", "ats": "ashby", "token": "postman", "sector": "DevTools"},
    {"name": "Luma AI", "domain": "lumalabs.ai", "ats": "ashby", "token": "luma-ai", "sector": "AI/3D"},
    {"name": "Weights & Biases", "domain": "wandb.ai", "ats": "ashby", "token": "wandb", "sector": "AI/MLOps"},
    {"name": "Replicate", "domain": "replicate.com", "ats": "ashby", "token": "replicate", "sector": "AI/Cloud"},

    # Greenhouse Top Tech & Startups
    {"name": "Stripe", "domain": "stripe.com", "ats": "greenhouse", "token": "stripe", "sector": "Fintech"},
    {"name": "Figma", "domain": "figma.com", "ats": "greenhouse", "token": "figma", "sector": "Design/SaaS"},
    {"name": "GitLab", "domain": "gitlab.com", "ats": "greenhouse", "token": "gitlab", "sector": "DevTools"},
    {"name": "Databricks", "domain": "databricks.com", "ats": "greenhouse", "token": "databricks", "sector": "Data/AI"},
    {"name": "Discord", "domain": "discord.com", "ats": "greenhouse", "token": "discord", "sector": "Consumer/Comms"},
    {"name": "Plaid", "domain": "plaid.com", "ats": "greenhouse", "token": "plaid", "sector": "Fintech"},
    {"name": "Brex", "domain": "brex.com", "ats": "greenhouse", "token": "brex", "sector": "Fintech"},
    {"name": "Robinhood", "domain": "robinhood.com", "ats": "greenhouse", "token": "robinhood", "sector": "Fintech"},
    {"name": "Coinbase", "domain": "coinbase.com", "ats": "greenhouse", "token": "coinbase", "sector": "Crypto"},
    {"name": "Carta", "domain": "carta.com", "ats": "greenhouse", "token": "carta", "sector": "Fintech"},
    {"name": "Instacart", "domain": "instacart.com", "ats": "greenhouse", "token": "instacart", "sector": "Consumer"},
    {"name": "DoorDash", "domain": "doordash.com", "ats": "greenhouse", "token": "doordash", "sector": "Logistics"},
    {"name": "Pinterest", "domain": "pinterest.com", "ats": "greenhouse", "token": "pinterest", "sector": "Social"},
    {"name": "Airbnb", "domain": "airbnb.com", "ats": "greenhouse", "token": "airbnb", "sector": "Travel"},
    {"name": "Reddit", "domain": "reddit.com", "ats": "greenhouse", "token": "reddit", "sector": "Social"},
    {"name": "Twilio", "domain": "twilio.com", "ats": "greenhouse", "token": "twilio", "sector": "Cloud/API"},
    {"name": "MongoDB", "domain": "mongodb.com", "ats": "greenhouse", "token": "mongodb", "sector": "Database"},
    {"name": "HashiCorp", "domain": "hashicorp.com", "ats": "greenhouse", "token": "hashicorp", "sector": "DevOps"},
    {"name": "Checkr", "domain": "checkr.com", "ats": "greenhouse", "token": "checkr", "sector": "HRTech"},
    {"name": "Sentry", "domain": "sentry.io", "ats": "greenhouse", "token": "sentry", "sector": "DevTools"},
    {"name": "Gusto", "domain": "gusto.com", "ats": "greenhouse", "token": "gusto", "sector": "HRTech"},
    {"name": "Razorpay", "domain": "razorpay.com", "ats": "greenhouse", "token": "razorpay", "sector": "Fintech"},
    {"name": "Zepto", "domain": "zeptonow.com", "ats": "greenhouse", "token": "zepto", "sector": "QuickCommerce"},
    {"name": "Groww", "domain": "groww.in", "ats": "greenhouse", "token": "groww", "sector": "Fintech"},
    {"name": "Swiggy", "domain": "swiggy.com", "ats": "greenhouse", "token": "swiggy", "sector": "Consumer/Tech"},
    {"name": "Meesho", "domain": "meesho.com", "ats": "greenhouse", "token": "meesho", "sector": "E-Commerce"},
    {"name": "Kite / Zerodha", "domain": "zerodha.com", "ats": "greenhouse", "token": "zerodha", "sector": "Fintech"},
    {"name": "CRED", "domain": "cred.club", "ats": "greenhouse", "token": "cred", "sector": "Fintech"},
    {"name": "BrowserStack", "domain": "browserstack.com", "ats": "greenhouse", "token": "browserstack", "sector": "DevTools"},

    # Lever Top Tech & Startups
    {"name": "Netflix", "domain": "netflix.com", "ats": "lever", "token": "netflix", "sector": "Media/Streaming"},
    {"name": "Shopify", "domain": "shopify.com", "ats": "lever", "token": "shopify", "sector": "E-Commerce"},
    {"name": "Affirm", "domain": "affirm.com", "ats": "lever", "token": "affirm", "sector": "Fintech"},
    {"name": "Webflow", "domain": "webflow.com", "ats": "lever", "token": "webflow", "sector": "Design/Web"},
    {"name": "Benchling", "domain": "benchling.com", "ats": "lever", "token": "benchling", "sector": "Biotech/SaaS"},
    {"name": "Loom (Atlassian)", "domain": "loom.com", "ats": "lever", "token": "loom", "sector": "Video/SaaS"},
    {"name": "Hugging Face", "domain": "huggingface.co", "ats": "lever", "token": "huggingface", "sector": "AI"},
    {"name": "Kustomer", "domain": "kustomer.com", "ats": "lever", "token": "kustomer", "sector": "CRM"},
    {"name": "Automattic", "domain": "automattic.com", "ats": "lever", "token": "automattic", "sector": "CMS/Remote"},
    {"name": "Kraken", "domain": "kraken.com", "ats": "lever", "token": "kraken", "sector": "Crypto"},
    {"name": "InVision", "domain": "invisionapp.com", "ats": "lever", "token": "invision", "sector": "Design"},
    {"name": "Karat", "domain": "karat.com", "ats": "lever", "token": "karat", "sector": "TechInterviewing"},
    {"name": "Docker", "domain": "docker.com", "ats": "lever", "token": "docker", "sector": "DevOps"},

    # Workable & SmartRecruiters Seeds
    {"name": "Clever", "domain": "clever.com", "ats": "workable", "token": "clever", "sector": "EdTech"},
    {"name": "Square (Block)", "domain": "block.xyz", "ats": "smartrecruiters", "token": "Square", "sector": "Fintech"},
    {"name": "Twitter / X Corp", "domain": "x.com", "ats": "smartrecruiters", "token": "Twitter", "sector": "Social"},
    {"name": "Visa", "domain": "visa.com", "ats": "smartrecruiters", "token": "Visa", "sector": "Payments"},
    {"name": "Bosch", "domain": "bosch.com", "ats": "smartrecruiters", "token": "BoschGroup", "sector": "Engineering/IoT"},
]

# GitHub URLs for community seed datasets
LEVERGREEN_REPO_RAW_URLS = [
    "https://raw.githubusercontent.com/adgramigna/job-board-scraper/main/data/companies.csv",
    "https://raw.githubusercontent.com/adgramigna/job-board-scraper/main/seeds/companies.csv",
    "https://raw.githubusercontent.com/adgramigna/job-board-scraper/master/companies.json",
]


def fetch_remote_seeds(timeout: float = 6.0) -> list[dict[str, str]]:
    """Attempt to fetch live seed databases from Levergreen / GitHub.
    
    Falls back gracefully if GitHub is rate-limiting or files moved.
    """
    discovered: list[dict[str, str]] = []
    headers = {"User-Agent": "ApplyPilot/0.2.0 (SeedHarvester)"}
    with httpx.Client(timeout=timeout, headers=headers, follow_redirects=True) as client:
        for url in LEVERGREEN_REPO_RAW_URLS:
            try:
                resp = client.get(url)
                if resp.status_code == 200 and resp.text:
                    if url.endswith(".csv"):
                        reader = csv.DictReader(io.StringIO(resp.text))
                        for row in reader:
                            # Map standard column variants
                            name = row.get("company_name") or row.get("name") or row.get("company")
                            token = row.get("ats_board_token") or row.get("board_token") or row.get("token") or row.get("slug")
                            ats = row.get("ats_provider") or row.get("ats") or row.get("job_board")
                            domain = row.get("domain") or row.get("official_domain") or row.get("website")
                            if name and token and ats:
                                discovered.append({
                                    "name": name.strip(),
                                    "token": token.strip(),
                                    "ats": ats.strip().lower(),
                                    "domain": domain.strip() if domain else "",
                                    "sector": row.get("sector", "Tech"),
                                })
                    elif url.endswith(".json"):
                        data = resp.json()
                        if isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict):
                                    name = item.get("name") or item.get("company")
                                    token = item.get("token") or item.get("slug")
                                    ats = item.get("ats") or item.get("ats_provider")
                                    if name and token and ats:
                                        discovered.append({
                                            "name": str(name).strip(),
                                            "token": str(token).strip(),
                                            "ats": str(ats).strip().lower(),
                                            "domain": str(item.get("domain", "")).strip(),
                                            "sector": str(item.get("sector", "Tech")),
                                        })
                    if discovered:
                        logger.info("Fetched %d remote seeds from %s", len(discovered), url)
                        break
            except Exception as e:
                logger.debug("Remote seed fetch notice for %s: %s", url, e)
    return discovered


def import_ats_seeds_to_watchlist(
    include_curated: bool = True,
    include_remote: bool = True,
    poll_now: bool = False,
    limit: int = 500,
    role_filter: list[str] | None = None,
) -> dict[str, Any]:
    """Ingest Levergreen & curated ATS company tokens into career_watchlist.

    Args:
        include_curated: Whether to ingest ApplyPilot's curated tech seeds.
        include_remote: Whether to fetch live seeds from open GitHub repositories.
        poll_now: If True, immediately query ATS public JSON feeds for live jobs.
        limit: Max companies to import.
        role_filter: Filter keywords for open jobs when poll_now is True.

    Returns:
        Summary dict of imported companies and discovered jobs.
    """
    candidates: list[dict[str, str]] = []

    if include_curated:
        candidates.extend(CURATED_ATS_SEEDS)

    if include_remote:
        remote = fetch_remote_seeds()
        candidates.extend(remote)

    # Deduplicate candidates by (ats, token)
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, str]] = []
    for c in candidates:
        key = (c.get("ats", "").lower(), c.get("token", "").lower())
        if key not in seen and key[0] and key[1]:
            seen.add(key)
            deduped.append(c)

    if limit > 0:
        deduped = deduped[:limit]

    conn = get_connection()
    imported_count = 0
    updated_count = 0

    for item in deduped:
        ats = item.get("ats", "").lower()
        token = item.get("token", "")
        name = item.get("name", token.title())
        domain = item.get("domain") or f"{token}.com"
        sector = item.get("sector", "Tech")

        # Map ats to direct board url
        if ats == "greenhouse":
            careers_url = f"https://boards.greenhouse.io/{token}"
        elif ats == "lever":
            careers_url = f"https://jobs.lever.co/{token}"
        elif ats == "ashby":
            careers_url = f"https://jobs.ashbyhq.com/{token}"
        elif ats == "workable":
            careers_url = f"https://apply.workable.com/{token}"
        elif ats == "smartrecruiters":
            careers_url = f"https://jobs.smartrecruiters.com/{token}"
        else:
            careers_url = f"https://{domain}/careers"

        try:
            upsert_career_watchlist(
                company_name=name,
                official_domain=domain,
                careers_page_url=careers_url,
                ats_provider=ats,
                ats_board_token=token,
                slug=token,
                priority_tier=1 if sector == "AI" else 2,
                is_vip=1 if sector == "AI" else 0,
                sector=sector,
                location="Remote / Worldwide",
                conn=conn,
            )
            imported_count += 1
        except Exception as e:
            logger.debug("Watchlist upsert note for %s: %s", name, e)

    jobs_discovered = 0
    if poll_now:
        logger.info("Polling %d ATS boards for live jobs...", len(deduped))
        keywords = [k.lower() for k in (role_filter or ["software", "engineer", "developer", "ai", "full stack", "backend", "frontend", "python"])]
        all_jobs: list[dict[str, Any]] = []

        for item in deduped:
            ats = item.get("ats", "").lower()
            token = item.get("token", "")
            cname = item.get("name", token.title())
            try:
                jobs = poll_board(ats, token)
                for j in jobs:
                    title = (j.get("title") or "").lower()
                    if any(k in title for k in keywords):
                        j["company"] = cname
                        j["site"] = ats
                        j["strategy"] = "ats_direct_feed"
                        all_jobs.append(j)
            except Exception as e:
                logger.debug("ATS poll error for %s (%s): %s", cname, token, e)

        if all_jobs:
            new_count, _ = store_jobs(conn=conn, jobs=all_jobs, site="levergreen_ats", strategy="ats_direct_feed")
            jobs_discovered = new_count

    logger.info("Levergreen ATS seed import complete: %d companies in watchlist, %d jobs discovered",
                imported_count, jobs_discovered)

    return {
        "companies_imported": imported_count,
        "companies_total_evaluated": len(deduped),
        "jobs_discovered": jobs_discovered,
    }


def test_seed_ingestion() -> bool:
    """Smoke test for Levergreen ATS seed ingestion."""
    result = import_ats_seeds_to_watchlist(
        include_curated=True,
        include_remote=False,
        poll_now=False,
        limit=5,
    )
    assert result["companies_imported"] > 0, "Curated seeds failed to import"
    return True
