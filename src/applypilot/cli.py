"""ApplyPilot CLI — the main entry point."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from applypilot import __version__
from applypilot import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)

app = typer.Typer(
    name="applypilot",
    help="AI-powered end-to-end job application pipeline.",
    no_args_is_help=True,
)
console = Console()
log = logging.getLogger(__name__)

# Valid pipeline stages (in execution order)
VALID_STAGES = ("discover", "enrich", "score", "tailor", "cover", "pdf")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bootstrap() -> None:
    """Common setup: load env, create dirs, init DB."""
    from applypilot.config import load_env, ensure_dirs
    from applypilot.database import init_db
    from applypilot.learning.migrations import run_migrations

    load_env()
    ensure_dirs()
    init_db()
    run_migrations()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"[bold]applypilot[/bold] {__version__}")
        raise typer.Exit()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """ApplyPilot — AI-powered end-to-end job application pipeline."""


@app.command()
def init() -> None:
    """Run the first-time setup wizard (profile, resume, search config)."""
    from applypilot.wizard.init import run_wizard

    run_wizard()


@app.command()
def run(
    stages: Optional[list[str]] = typer.Argument(
        None,
        help=(
            "Pipeline stages to run. "
            f"Valid: {', '.join(VALID_STAGES)}, all. "
            "Defaults to 'all' if omitted."
        ),
    ),
    min_score: int = typer.Option(
        config.DEFAULTS["min_score"], "--min-score",
        help=f"Minimum fit score for tailor/cover stages (default: {config.DEFAULTS['min_score']}).",
    ),
    max_age_days: int = typer.Option(
        config.DEFAULTS["max_job_age_days"], "--max-age-days",
        help=(
            "Skip jobs whose discovered_at is older than this many days. "
            "0 = no age filter. "
            f"Default: {config.DEFAULTS['max_job_age_days']}."
        ),
    ),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Max jobs per stage (tailor/cover). Default: 20."),
    workers: int = typer.Option(
        1, "--workers", "-w",
        help="Parallel threads for Workday/smart-extract stages. (JobSpy runs sequentially regardless.)",
    ),
    stream: bool = typer.Option(False, "--stream", help="Run stages concurrently (streaming mode)."),
    doc_format: str = typer.Option("docx", "--doc-format", help="Document format for resumes/cover letters: docx (default) or pdf."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview stages without executing."),
    source: Optional[list[str]] = typer.Option(
        None, "--source", "-s",
        help="Discovery source(s) to run. Repeatable: --source hn --source jobspy. "
             "Aliases: hn=hackernews, smart=smartextract. Only affects the discover stage.",
    ),
    list_sources: bool = typer.Option(
        False, "--list-sources",
        help="List available discovery sources and exit.",
    ),
) -> None:
    """Run pipeline stages: discover, enrich, score, tailor, cover, pdf."""
    # Handle --list-sources before bootstrap (no DB/env needed)
    if list_sources:
        from applypilot.pipeline import DISCOVERY_SOURCES, _SOURCE_ALIASES
        console.print("\n[bold]Available discovery sources:[/bold]\n")
        for name, desc in DISCOVERY_SOURCES.items():
            aliases = [a for a, canon in _SOURCE_ALIASES.items() if canon == name]
            alias_str = f"  (alias: {', '.join(aliases)})" if aliases else ""
            console.print(f"  [cyan]{name:<14s}[/cyan] {desc}{alias_str}")
        console.print("\nUsage: applypilot run discover --source hn --source jobspy")
        raise typer.Exit()

    _bootstrap()

    from applypilot.pipeline import run_pipeline, resolve_source_names

    stage_list = stages if stages else ["all"]

    # Validate stage names
    for s in stage_list:
        if s != "all" and s not in VALID_STAGES:
            console.print(
                f"[red]Unknown stage:[/red] '{s}'. "
                f"Valid stages: {', '.join(VALID_STAGES)}, all"
            )
            raise typer.Exit(code=1)

    # Resolve --source aliases
    resolved_sources: list[str] | None = None
    if source:
        try:
            resolved_sources = resolve_source_names(source)
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(code=1)

    # Validate --doc-format
    from applypilot.scoring.pdf import VALID_DOC_FORMATS
    if doc_format not in VALID_DOC_FORMATS:
        console.print(f"[red]Invalid --doc-format:[/red] '{doc_format}'. Must be one of: {', '.join(VALID_DOC_FORMATS)}")
        raise typer.Exit(code=1)

    # Gate AI stages behind Tier 2
    llm_stages = {"score", "tailor", "cover"}
    if any(s in stage_list for s in llm_stages) or "all" in stage_list:
        from applypilot.config import check_tier
        check_tier(2, "AI scoring/tailoring")

    result = run_pipeline(
        stages=stage_list,
        min_score=min_score,
        max_age_days=max_age_days,
        limit=limit,
        dry_run=dry_run,
        stream=stream,
        workers=workers,
        sources=resolved_sources,
        doc_format=doc_format,
    )

    if result.get("errors"):
        raise typer.Exit(code=1)


@app.command("discover-all")
def discover_all(
    sources: Optional[list[str]] = typer.Option(
        None, "--source", "-s",
        help="Sources to query: reddit, dorks, watchlist. Can be specified multiple times.",
    ),
    keywords: Optional[list[str]] = typer.Option(
        None, "--keyword", "-k",
        help="Role keywords to filter search dorks (e.g. Python, AI).",
    ),
    limit: int = typer.Option(30, "--limit", "-l", help="Max items per source."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview discovered jobs and leads without saving."),
) -> None:
    """Discover fresh hiring posts across Reddit, social dorks, and direct ATS boards."""
    _bootstrap()
    from applypilot.discovery import run_omni_channel_discovery
    console.print("[bold blue]Starting Omni-Channel Job & HR Discovery...[/bold blue]")
    summary = run_omni_channel_discovery(
        sources=sources,
        role_keywords=keywords,
        dry_run=dry_run,
        limit=limit,
    )
    console.print(f"[bold green]Discovery complete![/bold green] Total found: {summary['total_discovered']}")
    console.print(f"  • Reddit Posts: {summary['reddit_posts_count']}")
    console.print(f"  • Social Dorks: {summary['dork_posts_count']}")
    console.print(f"  • ATS Watchlist Jobs: {summary['watchlist_jobs_count']}")
    console.print(f"  • HR Recruiter Leads: {summary['leads_count']}")
    console.print(f"  • Routes: {summary['route_counts']}")
    if dry_run:
        console.print("[dim](Dry run mode: no changes were committed to database)[/dim]")


@app.command("import-blr-map")
def import_blr_map(
    sectors: Optional[str] = typer.Option(
        None, "--sectors", "-s",
        help="Comma-separated sectors to filter (e.g. AI,SaaS,Deeptech,Fintech,Healthtech).",
    ),
    only_hiring: bool = typer.Option(
        False, "--only-hiring", help="Only import startups with open roles on the map.",
    ),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum startups to import."),
    no_deep: bool = typer.Option(
        False, "--no-deep", help="Skip crawling individual /company/[slug] profile pages.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview extracted startups, roles, and contacts without saving.",
    ),
) -> None:
    """Import startups from Bangalore Startup Map into VIP Top-500 Watchlist and recruiter leads."""
    _bootstrap()
    from applypilot.discovery.bangalore_map_harvester import import_bangalore_startups_to_watchlist
    console.print("[bold blue]Importing startups from Bangalore Startup Map (bangalorestartupmap.com)...[/bold blue]")
    sector_list = [s.strip() for s in sectors.split(",")] if sectors else None
    summary = import_bangalore_startups_to_watchlist(
        sectors=sector_list,
        only_hiring=only_hiring,
        limit=limit,
        fetch_deep=not no_deep,
        dry_run=dry_run,
    )
    console.print(f"[bold green]Import complete![/bold green] Status: {summary.get('status')}")
    console.print(f"  • Total startups on map: {summary.get('total_startups_on_map', 0)}")
    console.print(f"  • Matching criteria: {summary.get('matching_startups_found', 0)}")
    console.print(f"  • Imported to VIP Watchlist: {summary.get('imported_companies', 0)}")
    console.print(f"  • Open Roles Indexed: {summary.get('open_roles_indexed', 0)}")
    console.print(f"  • Recruiter/Founder Leads Created: {summary.get('recruiter_leads_created', 0)}")
    if dry_run:
        console.print("[dim](Dry run mode: no changes committed to database)[/dim]")


@app.command("harvest-cdx")
def harvest_cdx(
    sources: Optional[list[str]] = typer.Option(
        None, "--source", "-s",
        help="CDX sources: open_apply_jobs, commoncrawl, crtsh. Default: all.",
    ),
    limit: int = typer.Option(100, "--limit", "-l", help="Max portals to index per source."),
    sync_db: bool = typer.Option(True, "--sync/--no-sync", help="Sync discovered portals to career_watchlist."),
) -> None:
    """Harvest ATS career portals from Common Crawl CDX, open-apply-jobs, and crt.sh."""
    _bootstrap()
    from applypilot.discovery.cdx_harvester import (
        bootstrap_from_open_apply_jobs,
        harvest_crtsh_career_subdomains,
        sync_slugs_to_watchlist,
    )
    console.print("[bold blue]Starting Internet Career Page & ATS Harvester...[/bold blue]")
    src_set = set(sources) if sources else {"open_apply_jobs", "commoncrawl", "crtsh"}
    total_found = 0
    if "open_apply_jobs" in src_set:
        hf_slugs = bootstrap_from_open_apply_jobs(limit_per_ats=limit)
        console.print(f"  • open-apply-jobs Hugging Face: {sum(len(v) for v in hf_slugs.values())} portals")
        if sync_db:
            sync_slugs_to_watchlist(hf_slugs)
            total_found += sum(len(v) for v in hf_slugs.values())
    if "crtsh" in src_set:
        subdomains = harvest_crtsh_career_subdomains(limit=limit)
        console.print(f"  • crt.sh Career Subdomains: {len(subdomains)} subdomains")
        total_found += len(subdomains)
    console.print(f"[bold green]Harvesting completed![/bold green] Total portals: {total_found}")


@app.command("enrich-leads")
def enrich_leads(
    min_emails: int = typer.Option(5, "--min-emails", "-m", help="Target minimum emails per company (e.g. 5 to 10)."),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum companies to process."),
    vip_only: bool = typer.Option(True, "--vip-only/--all", help="Process only VIP Top-Watchlist companies."),
) -> None:
    """Loop across watchlist companies and deeply enrich 5-10 verified emails per company."""
    _bootstrap()
    from applypilot.discovery.bangalore_map_harvester import enrich_all_watchlist_companies
    console.print(f"[bold blue]Deeply enriching company leads (target: {min_emails} emails/startup, limit: {limit})...[/bold blue]")
    summary = enrich_all_watchlist_companies(
        min_emails=min_emails,
        limit=limit,
        vip_only=vip_only,
    )
    console.print(f"[bold green]Enrichment complete![/bold green]")
    console.print(f"  • Companies Checked: {summary['total_companies_checked']}")
    console.print(f"  • Companies Enriched with new emails: {summary['companies_enriched']}")
    console.print(f"  • Total Emails Added to Leads: {summary['total_emails_added']}")


@app.command("import-yc")
def import_yc(
    india_only: bool = typer.Option(True, "--india-only/--global", help="Filter for YC startups in India/Bengaluru."),
    remote: bool = typer.Option(False, "--remote/--no-remote", help="Filter for YC startups hiring remotely."),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum YC startups to import."),
    enrich: bool = typer.Option(True, "--enrich/--no-enrich", help="Run deep email synthesis (5-10 emails/startup)."),
) -> None:
    """Import launched and hiring Y Combinator startups into VIP Watchlist and recruiter leads."""
    _bootstrap()
    from applypilot.discovery.yc_harvester import fetch_yc_startups, ingest_yc_startups_to_db
    console.print(f"[bold blue]Importing Y Combinator startups (india_only={india_only}, remote={remote}, limit={limit})...[/bold blue]")
    cos = fetch_yc_startups(india_only=india_only, remote_only=remote, hiring_only=True, limit=limit)
    stats = ingest_yc_startups_to_db(cos, enrich_emails=enrich)
    console.print("[bold green]YC import completed![/bold green]")
    console.print(f"  • Startups Ingested: {stats['startups_ingested']}")
    console.print(f"  • Domains Verified: {stats['domains_verified']}")
    console.print(f"  • Emails Enriched: {stats['emails_enriched']}")
    console.print(f"  • Recruiter/Founder Leads Created: {stats['leads_created']}")


@app.command("import-topstartups")
def import_topstartups(
    location: str = typer.Option("Bangalore", "--location", "-L", help="Job location filter: Bangalore or Remote."),
    pages: int = typer.Option(2, "--pages", "-p", help="Number of pages to scrape."),
    enrich: bool = typer.Option(True, "--enrich/--no-enrich", help="Run deep email synthesis for discovered startups."),
) -> None:
    """Scrape newly funded startups and direct ATS jobs from TopStartups.io."""
    _bootstrap()
    from applypilot.discovery.topstartups_harvester import ingest_topstartups_to_db, scrape_topstartups_jobs
    console.print(f"[bold blue]Scraping TopStartups.io (location={location}, pages={pages})...[/bold blue]")
    jobs_data = scrape_topstartups_jobs(location=location, max_pages=pages)
    stats = ingest_topstartups_to_db(jobs_data, enrich_emails=enrich)
    console.print("[bold green]TopStartups import completed![/bold green]")
    console.print(f"  • Companies Ingested: {stats['companies_ingested']}")
    console.print(f"  • Live ATS Jobs Stored: {stats['jobs_stored']}")
    console.print(f"  • Domains Verified: {stats['domains_verified']}")
    console.print(f"  • Recruiter Leads Created: {stats['leads_created']}")


@app.command("import-blr-arena")
def import_blr_arena(
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum Bangalore tech companies to import."),
    enrich: bool = typer.Option(True, "--enrich/--no-enrich", help="Run deep email synthesis for companies."),
) -> None:
    """Import Bangalore tech companies and open jobs from BLR Startup Arena."""
    _bootstrap()
    from applypilot.discovery.blr_arena_harvester import fetch_blr_arena_startups, ingest_blr_arena_to_db
    console.print(f"[bold blue]Importing BLR Startup Arena tech companies (limit={limit})...[/bold blue]")
    cos = fetch_blr_arena_startups(limit=limit)
    stats = ingest_blr_arena_to_db(cos, enrich_emails=enrich)
    console.print("[bold green]BLR Startup Arena import completed![/bold green]")
    console.print(f"  • Startups Ingested: {stats['startups_ingested']}")
    console.print(f"  • Domains Verified: {stats['domains_verified']}")
    console.print(f"  • Emails Enriched: {stats['emails_enriched']}")
    console.print(f"  • Recruiter Leads Created: {stats['leads_created']}")


@app.command("harvest-vc-boards")
def harvest_vc_boards(
    board: str = typer.Option("all", "--board", "-b", help="VC board to harvest: all, accel, khosla, lightspeed, general_catalyst, thrive."),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum jobs to harvest."),
    enrich: bool = typer.Option(True, "--enrich/--no-enrich", help="Run deep email synthesis for startups."),
) -> None:
    """Harvest verified startup jobs and portfolio companies from Getro and Consider VC talent networks."""
    _bootstrap()
    from applypilot.discovery.vc_portfolio_harvester import (
        fetch_consider_board_jobs,
        fetch_getro_board_jobs,
        ingest_vc_jobs_to_db,
    )
    console.print(f"[bold blue]Harvesting VC Portfolio Talent Boards (board={board}, limit={limit})...[/bold blue]")
    jobs_collected = []
    if board in ("all", "accel"):
        jobs_collected.extend(fetch_getro_board_jobs("accel", hits_per_page=limit))
    if board in ("all", "khosla"):
        jobs_collected.extend(fetch_getro_board_jobs("khosla", hits_per_page=limit))
    if board in ("all", "general_catalyst"):
        jobs_collected.extend(fetch_getro_board_jobs("general_catalyst", hits_per_page=limit))
    if board in ("all", "thrive"):
        jobs_collected.extend(fetch_getro_board_jobs("thrive", hits_per_page=limit))
    if board in ("all", "lightspeed"):
        jobs_collected.extend(fetch_consider_board_jobs("lightspeed"))

    jobs_collected = jobs_collected[:limit]
    stats = ingest_vc_jobs_to_db(jobs_collected, vc_source=f"VC Board ({board})", enrich_emails=enrich)
    console.print("[bold green]VC Talent Boards harvest completed![/bold green]")
    console.print(f"  • Portfolio Startups Ingested: {stats['companies_ingested']}")
    console.print(f"  • Live ATS Jobs Stored: {stats['jobs_stored']}")
    console.print(f"  • Recruiter Leads Created: {stats['leads_created']}")
    console.print(f"  • Domains Verified: {stats['domains_verified']}")


@app.command("import-fundraising-founders")
def import_fundraising_founders(
    limit: int = typer.Option(50, "--limit", "-l", help="Max founders to import."),
    enrich: bool = typer.Option(True, "--enrich/--no-enrich", help="Run deep email synthesis."),
) -> None:
    """Import Bengaluru & Indian startup founders and personal LinkedIn URLs from startupfundraising.com."""
    _bootstrap()
    from applypilot.discovery.startupfundraising_harvester import (
        fetch_startupfundraising_html,
        parse_founders_html,
        ingest_fundraising_founders_to_db,
    )
    console.print(f"[bold blue]Importing StartupFundraising Founders (limit={limit})...[/bold blue]")
    html = fetch_startupfundraising_html()
    founders = parse_founders_html(html)[:limit]
    stats = ingest_fundraising_founders_to_db(founders, enrich_emails=enrich)
    console.print("[bold green]StartupFundraising import completed![/bold green]")
    console.print(f"  • Founders Ingested: {stats['founders_ingested']}")
    console.print(f"  • Companies Ingested: {stats['companies_ingested']}")
    console.print(f"  • Recruiter/Founder Leads Created: {stats['leads_created']}")
    console.print(f"  • LinkedIn Notes Generated: {stats['notes_generated']}")


@app.command("import-startupmap-one")
def import_startupmap_one(
    limit: int = typer.Option(50, "--limit", "-l", help="Max jobs to import."),
    remote: bool = typer.Option(False, "--remote", help="Fetch remote feed instead of Bengaluru."),
    enrich: bool = typer.Option(True, "--enrich/--no-enrich", help="Run deep email synthesis."),
) -> None:
    """Import curated startup jobs and ATS links from startupmap.one."""
    _bootstrap()
    from applypilot.discovery.startupmap_one_harvester import (
        fetch_startupmap_html,
        parse_startupmap_jobs,
        ingest_startupmap_jobs_to_db,
        STARTUPMAP_BLR_URL,
        STARTUPMAP_REMOTE_URL,
    )
    target_url = STARTUPMAP_REMOTE_URL if remote else STARTUPMAP_BLR_URL
    console.print(f"[bold blue]Importing StartupMap.one jobs ({target_url})...[/bold blue]")
    html = fetch_startupmap_html(target_url)
    jobs = parse_startupmap_jobs(html)[:limit]
    stats = ingest_startupmap_jobs_to_db(jobs, enrich_emails=enrich)
    console.print("[bold green]StartupMap.one import completed![/bold green]")
    console.print(f"  • Companies Ingested: {stats['companies_ingested']}")
    console.print(f"  • Jobs Stored: {stats['jobs_stored']}")


@app.command("loop-companies")
def loop_companies(
    tier: int = typer.Option(1, "--tier", "-t", help="Priority tier to sweep (1 for VIP Top-500, 2 for Global Index)."),
    vip_only: bool = typer.Option(False, "--vip-only", help="Only sweep VIP-flagged companies."),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum companies to process in this sweep."),
    target_emails: int = typer.Option(8, "--target-emails", help="Target verified emails per company (5-15)."),
    enrich: bool = typer.Option(True, "--enrich/--no-enrich", help="Run deep email synthesis."),
    poll_jobs: bool = typer.Option(True, "--poll-jobs/--no-poll-jobs", help="Poll 11 ATS platforms and check JSON-LD for new job launches."),
) -> None:
    """Deeply loop through watchlist companies: maximize verified emails & detect real-time job launches."""
    _bootstrap()
    from applypilot.discovery.company_deep_looper import loop_all_watchlist_companies
    console.print(f"[bold blue]Starting Deep Company Looper (tier<={tier}, limit={limit}, target_emails={target_emails})...[/bold blue]")
    summary = loop_all_watchlist_companies(
        priority_tier=tier,
        vip_only=vip_only,
        limit=limit,
        target_emails=target_emails,
        enrich_emails=enrich,
        poll_jobs=poll_jobs,
    )
    console.print("[bold green]Deep Company Looping Sweep Complete![/bold green]")
    console.print(f"  • Companies Processed: {summary['companies_processed']}")
    console.print(f"  • Verified Emails Added: {summary['total_emails_added']}")
    console.print(f"  • Brand New Jobs Found on Launch: {summary['total_new_jobs_found']}")
    console.print(f"  • Companies with New Openings: {summary['companies_with_new_jobs']}")


@app.command("harvest-all-directories")
def harvest_all_directories(
    limit: int = typer.Option(30, "--limit", "-l", help="Limit per directory source."),
    enrich: bool = typer.Option(True, "--enrich/--no-enrich", help="Run deep email synthesis."),
) -> None:
    """Execute omni-directory harvest across Bangalore Map, YC, TopStartups, BLR Arena, VC Boards, and Founders."""
    _bootstrap()
    from applypilot.discovery.multi_directory_orchestrator import run_omni_startup_harvest
    console.print("[bold blue]Launching Omni-Directory Startup & Job Harvest across all sources...[/bold blue]")
    summary = run_omni_startup_harvest(
        include_bangalore_map=True,
        include_yc=True,
        include_topstartups=True,
        include_blr_arena=True,
        include_vc_boards=True,
        include_startupfundraising=True,
        include_startupmap_one=True,
        limit_per_source=limit,
        enrich_emails=enrich,
    )
    console.print("[bold green]Omni-Directory harvest completed![/bold green]")
    console.print(f"  • Total Startups Ingested: {summary['total_startups_ingested']}")
    console.print(f"  • Total Live Jobs Stored: {summary['total_jobs_stored']}")
    console.print(f"  • Total Recruiter/Founder Leads Created: {summary['total_leads_created']}")
    console.print(f"  • Total Verified Domains: {summary['total_domains_verified']}")



@app.command("outreach")
def outreach(
    mode: str = typer.Option("draft", "--mode", "-m", help="Execution mode: draft (creates Gmail Drafts) or auto_send."),
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum leads to reach out to."),
    min_score: int = typer.Option(70, "--min-score", help="Minimum fit score threshold."),
) -> None:
    """Execute hyper-tailored email outreach to recruiters and founders for discovered leads."""
    _bootstrap()
    from applypilot.outreach.mailer import run_hr_outreach
    console.print(f"[bold blue]Executing HR/Founder Outreach (mode: {mode})...[/bold blue]")
    summary = run_hr_outreach(mode=mode, limit=limit, min_score=min_score)
    console.print("[bold green]Outreach completed![/bold green]")
    console.print(f"  • Processed: {summary['processed']}")
    console.print(f"  • Drafted: {summary['drafted']}")
    console.print(f"  • Sent: {summary['sent']}")
    console.print(f"  • Parked for HITL review: {summary['parked_hitl']}")
    console.print(f"  • Skipped (awaiting portal apply first): {summary['skipped_dual_attack']}")


@app.command("run-daily")
def run_daily(
    limit: int = typer.Option(10, "--limit", "-l", help="Max jobs to discover and process per channel."),
    min_score: int = typer.Option(70, "--min-score", help="Minimum fit score threshold."),
    outreach_mode: str = typer.Option("draft", "--mode", "-m", help="HR outreach mode: draft or auto_send."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview daily pipeline run without committing changes."),
) -> None:
    """Execute the full autonomous daily job acquisition pipeline."""
    _bootstrap()
    from applypilot.daily_runner import run_daily_pipeline
    console.print("[bold blue]Starting ApplyPilot Autonomous Daily Job Acquisition Pipeline...[/bold blue]")
    report = run_daily_pipeline(
        dry_run=dry_run,
        min_score=min_score,
        limit=limit,
        outreach_mode=outreach_mode,
    )
    console.print("[bold green]Daily pipeline run complete![/bold green]")
    if dry_run:
        console.print("[dim](Dry run mode: changes were not committed)[/dim]")


@app.command()
def apply(
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Max applications to submit."),
    workers: int = typer.Option(5, "--workers", "-w", help="Number of parallel browser workers."),
    min_score: int = typer.Option(
        config.DEFAULTS["min_score"], "--min-score",
        help=f"Minimum fit score for job selection (default: {config.DEFAULTS['min_score']}).",
    ),
    max_age_days: int = typer.Option(
        config.DEFAULTS["max_job_age_days"], "--max-age-days",
        help=(
            "Skip jobs whose discovered_at is older than this many days. "
            "0 = no age filter. "
            f"Default: {config.DEFAULTS['max_job_age_days']}."
        ),
    ),
    max_score: Optional[int] = typer.Option(None, "--max-score", help="Maximum fit score for job selection (useful for testing on lower-score jobs)."),
    model: str = typer.Option("sonnet", "--model", "-m", help="Claude model name (sonnet | haiku | opus)."),
    continuous: bool = typer.Option(False, "--continuous", "-c", help="Run forever, polling for new jobs."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview actions without submitting."),
    headless: bool = typer.Option(False, "--headless", help="Run browsers in headless mode."),
    url: Optional[str] = typer.Option(None, "--url", help="Apply to a specific job URL."),
    doc_format: str = typer.Option("docx", "--doc-format", help="Document format for resumes/cover letters: docx (default) or pdf."),
    gen: bool = typer.Option(False, "--gen", help="Generate prompt file for manual debugging instead of running."),
    mark_applied: Optional[str] = typer.Option(None, "--mark-applied", help="Manually mark a job URL as applied."),
    fresh_sessions: bool = typer.Option(False, "--fresh-sessions", help="Refresh Chrome session cookies from your real profile before launching."),
    no_hitl: bool = typer.Option(False, "--no-hitl", help="Skip HITL waits: park needs_human jobs and move on. Use for overnight runs."),
    no_focus: bool = typer.Option(False, "--no-focus", help="Prevent Chrome windows from stealing keyboard focus (Linux/GNOME only). Windows stay visible but won't interrupt your active app."),
    mark_failed: Optional[str] = typer.Option(None, "--mark-failed", help="Manually mark a job URL as failed (provide URL)."),
    fail_reason: Optional[str] = typer.Option(None, "--fail-reason", help="Reason for --mark-failed."),
    reset_failed: bool = typer.Option(False, "--reset-failed", help="Reset all failed jobs for retry."),
    reset_category: Optional[str] = typer.Option(None, "--reset-category", help="Reset all jobs in a category for retry (e.g., blocked_technical)."),
    sessions: bool = typer.Option(False, "--sessions", help="List saved ATS sessions."),
    clear_session: Optional[str] = typer.Option(None, "--clear-session", help="Clear a saved ATS session (e.g., workday)."),
) -> None:
    """Launch auto-apply to submit job applications."""
    _bootstrap()

    from applypilot.config import check_tier, PROFILE_PATH as _profile_path
    from applypilot.database import get_connection

    # --- Utility modes (no Chrome/Claude needed) ---

    if mark_applied:
        from applypilot.apply.launcher import mark_job
        mark_job(mark_applied, "applied")
        console.print(f"[green]Marked as applied:[/green] {mark_applied}")
        return

    if mark_failed:
        from applypilot.apply.launcher import mark_job
        mark_job(mark_failed, "failed", reason=fail_reason)
        console.print(f"[yellow]Marked as failed:[/yellow] {mark_failed} ({fail_reason or 'manual'})")
        return

    if reset_failed:
        from applypilot.apply.launcher import reset_failed as do_reset
        count = do_reset()
        console.print(f"[green]Reset {count} failed job(s) for retry.[/green]")
        return

    if reset_category:
        from applypilot.database import reset_by_category
        count = reset_by_category(reset_category)
        console.print(f"[green]Reset {count} job(s) in category '{reset_category}' for retry.[/green]")
        return

    if sessions:
        from applypilot.apply.chrome import list_ats_sessions
        ats_sessions = list_ats_sessions()
        if not ats_sessions:
            console.print("[dim]No saved ATS sessions.[/dim]")
            return
        t = Table(title="Saved ATS Sessions", show_header=True, header_style="bold cyan")
        t.add_column("ATS")
        t.add_column("Cookies")
        t.add_column("Age")
        for s in ats_sessions:
            age_str = f"{s['age_hours']:.1f}h" if s["age_hours"] is not None else "n/a"
            t.add_row(s["slug"], "yes" if s["has_cookies"] else "no", age_str)
        console.print(t)
        return

    if clear_session:
        from applypilot.apply.chrome import clear_ats_session
        if clear_ats_session(clear_session):
            console.print(f"[green]Cleared ATS session: {clear_session}[/green]")
        else:
            console.print(f"[yellow]No session found for: {clear_session}[/yellow]")
        return

    # --- Full apply mode ---

    # Validate --doc-format
    from applypilot.scoring.pdf import VALID_DOC_FORMATS as _valid_fmts
    if doc_format not in _valid_fmts:
        console.print(f"[red]Invalid --doc-format:[/red] '{doc_format}'. Must be one of: {', '.join(_valid_fmts)}")
        raise typer.Exit(code=1)

    # Set doc format for apply workers
    from applypilot.apply.launcher import set_doc_format
    set_doc_format(doc_format)

    # Check 1: Tier 3 required (Claude Code CLI + Chrome)
    check_tier(3, "auto-apply")

    # Check 2: Profile exists
    if not _profile_path.exists():
        console.print(
            "[red]Profile not found.[/red]\n"
            "Run [bold]applypilot init[/bold] to create your profile first."
        )
        raise typer.Exit(code=1)

    # Check 3: Tailored resumes exist (skip for --gen with --url)
    if not (gen and url):
        conn = get_connection()
        ready = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE tailored_resume_path IS NOT NULL AND applied_at IS NULL"
        ).fetchone()[0]
        if ready == 0:
            console.print(
                "[red]No tailored resumes ready.[/red]\n"
                "Run [bold]applypilot run score tailor[/bold] first to prepare applications."
            )
            raise typer.Exit(code=1)

    if gen:
        from applypilot.apply.launcher import gen_prompt
        target = url or ""
        if not target:
            console.print("[red]--gen requires --url to specify which job.[/red]")
            raise typer.Exit(code=1)
        prompt_file = gen_prompt(target, min_score=min_score, max_score=max_score, model=model)
        if not prompt_file:
            console.print("[red]No matching job found for that URL.[/red]")
            raise typer.Exit(code=1)
        mcp_path = _profile_path.parent / ".mcp-apply-0.json"
        console.print(f"[green]Wrote prompt to:[/green] {prompt_file}")
        console.print("\n[bold]Run manually:[/bold]")
        console.print(
            f"  claude --model {model} -p "
            f"--mcp-config {mcp_path} "
            f"--permission-mode bypassPermissions < {prompt_file}"
        )
        return

    from applypilot.apply.launcher import main as apply_main

    effective_limit = limit if limit is not None else 0

    console.print("\n[bold blue]Launching Auto-Apply[/bold blue]")
    console.print(f"  Limit:    {'unlimited' if continuous else effective_limit}")
    console.print(f"  Workers:  {workers}")
    console.print(f"  Model:    {model}")
    console.print(f"  Headless: {headless}")
    console.print(f"  Dry run:  {dry_run}")
    if fresh_sessions:
        console.print("  Sessions: [yellow]refreshing from real Chrome profile[/yellow]")
    if url:
        console.print(f"  Target:   {url}")
    console.print()

    apply_main(
        limit=effective_limit,
        target_url=url,
        min_score=min_score,
        max_age_days=max_age_days,
        max_score=max_score,
        headless=headless,
        model=model,
        dry_run=dry_run,
        continuous=continuous,
        workers=workers,
        fresh_sessions=fresh_sessions,
        no_hitl=no_hitl,
        no_focus=no_focus,
    )


@app.command()
def status() -> None:
    """Show pipeline statistics from the database."""
    _bootstrap()

    from applypilot.database import get_stats

    stats = get_stats()

    console.print("\n[bold]ApplyPilot Pipeline Status[/bold]\n")

    # Summary table
    summary = Table(title="Pipeline Overview", show_header=True, header_style="bold cyan")
    summary.add_column("Metric", style="bold")
    summary.add_column("Count", justify="right")

    summary.add_row("Total jobs discovered", str(stats["total"]))
    summary.add_row("With full description", str(stats["with_description"]))
    summary.add_row("Pending enrichment", str(stats["pending_detail"]))
    summary.add_row("Enrichment errors", str(stats["detail_errors"]))
    summary.add_row("Scored by LLM", str(stats["scored"]))
    summary.add_row("Pending scoring", str(stats["unscored"]))
    summary.add_row("Tailored resumes", str(stats["tailored"]))
    summary.add_row("Pending tailoring (7+)", str(stats["untailored_eligible"]))
    summary.add_row("Cover letters", str(stats["with_cover_letter"]))
    summary.add_row("Ready to apply", str(stats["ready_to_apply"]))
    summary.add_row("Applied", str(stats["applied"]))
    summary.add_row("Apply errors", str(stats["apply_errors"]))
    if stats.get("needs_human", 0) > 0:
        summary.add_row("Needs human review", str(stats["needs_human"]))

    console.print(summary)

    # Score distribution
    if stats["score_distribution"]:
        dist_table = Table(title="\nScore Distribution", show_header=True, header_style="bold yellow")
        dist_table.add_column("Score", justify="center")
        dist_table.add_column("Count", justify="right")
        dist_table.add_column("Bar")

        max_count = max(count for _, count in stats["score_distribution"]) or 1
        for score, count in stats["score_distribution"]:
            bar_len = int(count / max_count * 30)
            if score >= 7:
                color = "green"
            elif score >= 5:
                color = "yellow"
            else:
                color = "red"
            bar = f"[{color}]{'=' * bar_len}[/{color}]"
            dist_table.add_row(str(score), str(count), bar)

        console.print(dist_table)

    # Score funnel: per-score breakdown of pipeline stages
    funnel = stats.get("score_funnel", [])
    if funnel:
        funnel_table = Table(
            title="\nPipeline Funnel by Score",
            show_header=True,
            header_style="bold magenta",
        )
        funnel_table.add_column("Score",        justify="center", style="bold")
        funnel_table.add_column("Cover Ready",  justify="right", style="green")
        funnel_table.add_column("Tailored",     justify="right", style="cyan")
        funnel_table.add_column("Needs Tailor", justify="right", style="yellow")
        funnel_table.add_column("Applied",      justify="right", style="dim green")
        funnel_table.add_column("Errors",       justify="right", style="red")

        for row in funnel:
            score = row["score"]
            score_str = f"[bold {'green' if score >= 9 else 'yellow' if score >= 7 else 'white'}]{score}[/]"
            funnel_table.add_row(
                score_str,
                str(row["cover_ready"])  if row["cover_ready"]  else "[dim]—[/]",
                str(row["tailored"])     if row["tailored"]     else "[dim]—[/]",
                str(row["needs_tailor"]) if row["needs_tailor"] else "[dim]—[/]",
                str(row["applied"])      if row["applied"]      else "[dim]—[/]",
                str(row["errors"])       if row["errors"]       else "[dim]—[/]",
            )

        console.print(funnel_table)

    # Apply categories with per-score breakdown
    by_cat = stats.get("by_category", {})
    if by_cat:
        cat_table = Table(title="\nApply Categories", show_header=True, header_style="bold blue")
        cat_table.add_column("Category", style="bold")
        cat_table.add_column("Total", justify="right")
        cat_table.add_column("10",  justify="right", style="bold green")
        cat_table.add_column("9",   justify="right", style="green")
        cat_table.add_column("8",   justify="right", style="yellow")
        cat_table.add_column("7",   justify="right", style="yellow")
        cat_table.add_column("6",   justify="right", style="dim")
        cat_table.add_column("<6",  justify="right", style="dim")
        cat_table.add_column("Action")

        cat_display = {
            "applied":             ("green",   "Done"),
            "pending":             ("white",   "In queue"),
            "in_progress":         ("cyan",    "Running now"),
            "needs_human":         ("magenta", "applypilot human-review"),
            "blocked_auth":        ("yellow",  "Needs persistent sessions / HITL"),
            "blocked_technical":   ("yellow",  "Retryable: applypilot reset-category blocked_technical"),
            "archived_ineligible": ("dim",     "Location/salary/type mismatch"),
            "archived_expired":    ("dim",     "Job no longer available"),
            "archived_platform":   ("red",     "Unsupported platform"),
            "archived_no_url":     ("dim",     "No application URL"),
            "manual_only":         ("dim",     "Manual ATS (no automation)"),
        }

        def _score_cell(d: dict, key: str) -> str:
            """Format a score count cell — blank if zero."""
            v = d.get(key, 0) if isinstance(d, dict) else 0
            return str(v) if v else "[dim]—[/dim]"

        order = ["applied", "pending", "in_progress", "needs_human",
                 "blocked_auth", "blocked_technical",
                 "archived_ineligible", "archived_expired",
                 "archived_platform", "archived_no_url", "manual_only"]
        for cat in order:
            d = by_cat.get(cat)
            if not d:
                continue
            total = d["total"] if isinstance(d, dict) else d
            color, action = cat_display.get(cat, ("white", ""))
            cat_table.add_row(
                f"[{color}]{cat}[/{color}]",
                str(total),
                _score_cell(d, "10"),
                _score_cell(d, "9"),
                _score_cell(d, "8"),
                _score_cell(d, "7"),
                _score_cell(d, "6"),
                _score_cell(d, "<6"),
                action,
            )

        # Any unknown categories
        for cat, d in sorted(by_cat.items(), key=lambda x: -(x[1]["total"] if isinstance(x[1], dict) else x[1])):
            if cat not in cat_display:
                total = d["total"] if isinstance(d, dict) else d
                if total > 0:
                    cat_table.add_row(
                        cat, str(total),
                        _score_cell(d, "10"), _score_cell(d, "9"),
                        _score_cell(d, "8"),  _score_cell(d, "7"),
                        _score_cell(d, "6"),  _score_cell(d, "<6"),
                        "",
                    )

        console.print(cat_table)

        # Retry hint for high-score retryable jobs
        retryable_tech = by_cat.get("blocked_technical", {})
        if isinstance(retryable_tech, dict):
            high_score_retryable = retryable_tech.get("10", 0) + retryable_tech.get("9", 0)
            if high_score_retryable > 0:
                console.print(
                    f"[bold yellow]  ↳ {high_score_retryable} score 9-10 jobs in blocked_technical are retryable.[/bold yellow]"
                    f" Run: [bold]applypilot reset-category blocked_technical[/bold]"
                )

    # By site (group all HN: * sites under "HackerNews")
    if stats["by_site"]:
        site_table = Table(title="\nJobs by Source", show_header=True, header_style="bold magenta")
        site_table.add_column("Site")
        site_table.add_column("Count", justify="right")

        grouped: dict[str, int] = {}
        for site, count in stats["by_site"]:
            key = "HackerNews" if (site or "").startswith("HN:") else (site or "Unknown")
            grouped[key] = grouped.get(key, 0) + count
        for site, count in sorted(grouped.items(), key=lambda x: -x[1]):
            site_table.add_row(site, str(count))

        console.print(site_table)

    # ── Funnel diagnostics ────────────────────────────────────────
    if stats.get("skipped_stale"):
        max_age = config.DEFAULTS["max_job_age_days"]
        console.print(
            f"\n[dim]Skipped as stale (>{max_age}d old): "
            f"{stats['skipped_stale']} ready-to-apply jobs[/dim]"
        )

    bbc = stats.get("blocked_by_cap") or {}
    if bbc.get("count"):
        console.print(
            f"\n[yellow]Blocked by company cap:[/yellow] "
            f"{bbc['count']} company/companies"
        )
        if bbc.get("companies"):
            preview = ", ".join(bbc["companies"][:10])
            more = f" (+{bbc['count'] - 10} more)" if bbc["count"] > 10 else ""
            console.print(f"  [dim]{preview}{more}[/dim]")

    # ── Pipeline state distribution (2026-04-24 state machine) ────
    from applypilot.database import get_connection as _get_conn
    _sc_conn = _get_conn()
    state_rows = _sc_conn.execute(
        "SELECT state, COUNT(*) FROM jobs WHERE state IS NOT NULL "
        "GROUP BY state ORDER BY COUNT(*) DESC"
    ).fetchall()
    if state_rows:
        state_table = Table(
            title="\nPipeline State Distribution",
            show_header=True, header_style="bold cyan",
        )
        state_table.add_column("State", style="bold")
        state_table.add_column("Count", justify="right")
        # Color-code by lifecycle phase.
        TERMINAL_OK = {"applied", "responded", "interview", "offer"}
        TERMINAL_BAD = {"rejected", "ghosted", "archived", "apply_failed",
                        "enrich_failed", "score_failed", "tailor_failed",
                        "cover_failed", "low_score"}
        ACTIVE = {"applying", "tailoring", "cover_writing",
                  "ready_to_apply", "needs_human"}
        for r in state_rows:
            st = r[0]
            n = r[1]
            if st in TERMINAL_OK:
                color = "green"
            elif st in TERMINAL_BAD:
                color = "dim"
            elif st in ACTIVE:
                color = "yellow"
            else:
                color = "cyan"
            state_table.add_row(f"[{color}]{st}[/{color}]", str(n))
        console.print(state_table)

    console.print()


@app.command()
def track(
    days: int = typer.Option(14, "--days", "-d", help="Email look-back period in days."),
    setup: bool = typer.Option(False, "--setup", help="Verify Gmail MCP connectivity."),
    actions: bool = typer.Option(False, "--actions", "-a", help="Show pending action items."),
    ghosted_days: int = typer.Option(7, "--ghosted-days", help="Days before marking as ghosted."),
    limit: int = typer.Option(100, "--limit", "-l", help="Max emails to fetch."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Fetch + classify but don't write DB/files."),
    relabel: bool = typer.Option(False, "--relabel", help="Apply 'ap-track' label to all emails already in the DB (backfill)."),
    remap_stubs: bool = typer.Option(False, "--remap-stubs", help="Re-match emails under multi-company stubs to correct per-company jobs."),
    poll_hitl: bool = typer.Option(False, "--poll-hitl", help="Poll Gmail for user replies to pending HITL email questions."),
) -> None:
    """Track application responses from Gmail and sync HITL email replies."""
    _bootstrap()

    from applypilot.config import check_tier
    check_tier(2, "application tracking")

    if poll_hitl:
        from applypilot.hitl.email_reply_parser import sync_email_hitl_replies
        console.print("[dim]Polling Gmail for user replies to pending HITL questions...[/dim]")
        hitl_res = sync_email_hitl_replies()
        if hitl_res.get("resolved_tickets"):
            console.print(f"[green]Resolved {len(hitl_res['resolved_tickets'])} HITL tickets: {hitl_res['requeued_jobs']}[/green]")
        else:
            console.print("[dim]No new HITL replies found.[/dim]")
        return

    if setup:
        import asyncio
        from applypilot.tracking.gmail_client import check_gmail_setup, verify_connection

        ok, msg = check_gmail_setup()
        if not ok:
            console.print(f"[red]{msg}[/red]")
            raise typer.Exit(code=1)

        console.print("[dim]Testing Gmail MCP connection...[/dim]")
        connected = asyncio.run(verify_connection())
        if connected:
            console.print("[green]Gmail MCP connected successfully.[/green]")
        else:
            console.print("[red]Gmail MCP connection failed.[/red]")
            console.print("[dim]Check that gcp-oauth.keys.json is valid and OAuth is authorized.[/dim]")
            raise typer.Exit(code=1)
        return

    if actions:
        from applypilot.tracking import show_action_items
        show_action_items()
        return

    if relabel:
        from applypilot.tracking import relabel_all_tracked
        relabel_all_tracked()
        return

    if remap_stubs:
        from applypilot.tracking import remap_stubs as _remap_stubs
        _remap_stubs()
        return

    from applypilot.tracking import run_tracking

    result = run_tracking(
        days=days,
        ghosted_days=ghosted_days,
        limit=limit,
        dry_run=dry_run,
    )

    if result.get("errors", 0) > 0:
        raise typer.Exit(code=1)


@app.command()
def learn(
    trace_file: Optional[Path] = typer.Option(None, "--trace-file", "-f", help="Path to apply_trace.jsonl"),
) -> None:
    """Analyze apply telemetry traces and promote verified selectors to Tier 0 cache."""
    _bootstrap()
    from applypilot.learning.pattern_compiler import promote_successful_traces

    console.print("[bold blue]Pattern Compiler (Stage 7 Learning)[/bold blue]")
    result = promote_successful_traces(trace_log_path=trace_file)
    console.print(
        f"  [green]Processed {result['total_processed']} traces, "
        f"promoted {result['promoted_count']} verified selectors into Tier 0 cache.[/green]"
    )
    if result.get("by_ats"):
        for ats, count in result["by_ats"].items():
            console.print(f"  • {ats}: {count} selectors promoted")


@app.command()
def mcp() -> None:
    """Start the ApplyPilot FastMCP server over stdio transport."""
    _bootstrap()
    from applypilot.mcp_server import run_server

    run_server()


def _find_dashboard_dir() -> Optional[Path]:
    """Locate the Next.js dashboard directory across local dev, Docker, and package environments."""
    candidates = [
        os.environ.get("APPLYPILOT_DASHBOARD_DIR"),
        Path.cwd() / "dashboard",
        Path(__file__).resolve().parent.parent.parent / "dashboard",
        Path("/home/applypilot/app/dashboard"),
    ]
    for c in candidates:
        if c:
            p = Path(c).resolve()
            if p.exists() and (p / "package.json").exists():
                return p
    return None


@app.command()
def dashboard(
    serve: bool = typer.Option(False, "--serve", "-s", help="Serve legacy dashboard over HTTP."),
    port: int = typer.Option(3000, "--port", "-p", help="HTTP port when serving."),
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host address to bind when serving."),
    next_ui: bool = typer.Option(True, "--next/--legacy", help="Launch the Next.js iOS liquid-glass dashboard (default: Next.js)."),
) -> None:
    """Launch the ApplyPilot dashboard (Next.js iOS liquid-glass UI or legacy static HTML)."""
    _bootstrap()

    if next_ui:
        import subprocess
        dashboard_dir = _find_dashboard_dir()
        if dashboard_dir:
            console.print(f"[bold green]Starting Next.js iOS Liquid-Glass Dashboard on port {port}...[/bold green]")
            console.print(f"[bold cyan]Open http://{host}:{port} in your browser.[/bold cyan]")
            try:
                # Prefer optimized production start if .next exists, else dev
                if (dashboard_dir / ".next").exists():
                    subprocess.run(
                        ["npx", "next", "start", "-H", host, "-p", str(port)],
                        cwd=str(dashboard_dir),
                        check=True,
                    )
                else:
                    subprocess.run(
                        ["npx", "next", "dev", "-H", host, "-p", str(port)],
                        cwd=str(dashboard_dir),
                        check=True,
                    )
            except KeyboardInterrupt:
                console.print("\n[dim]Dashboard server stopped.[/dim]")
            return
        else:
            console.print("[yellow]Next.js dashboard directory not found; falling back to legacy dashboard.[/yellow]")

    from applypilot.view import generate_dashboard, open_dashboard

    if serve:
        import functools
        import http.server
        import socketserver

        path = generate_dashboard()
        console.print(f"[bold green]Dashboard generated:[/bold green] {path}")
        console.print(f"[bold cyan]Serving at http://{host}:{port}/dashboard.html[/bold cyan]")
        console.print("[dim]Press Ctrl+C to stop.[/dim]")

        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(path.parent))
        with socketserver.TCPServer((host, port), handler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                console.print("\n[dim]Dashboard server stopped.[/dim]")
    else:
        open_dashboard()


# `applypilot human-review` was deleted in plan 5 of the apply UX overhaul.
# The standalone HITL server (port 7373) duplicated the in-pipeline HITL
# flow (port 7380+wid), so it was removed. Jobs that get parked as
# `needs_human` are now picked up automatically by the next
# `applypilot apply` run via _run_hitl's launcher-restart path.


# ---------------------------------------------------------------------------
# Q&A knowledge base commands
# ---------------------------------------------------------------------------

qa_app = typer.Typer(name="qa", help="Manage the Q&A knowledge base for screening questions.")
app.add_typer(qa_app)


@qa_app.command("list")
def qa_list(
    limit: int = typer.Option(50, "--limit", "-l", help="Max Q&A pairs to show."),
) -> None:
    """Show stored Q&A pairs from past applications."""
    _bootstrap()

    from applypilot.database import get_all_qa

    pairs = get_all_qa()
    if not pairs:
        console.print("[dim]No Q&A pairs stored yet. Apply to jobs to build the knowledge base.[/dim]")
        return

    t = Table(title=f"Q&A Knowledge Base ({len(pairs)} total)", show_header=True, header_style="bold cyan")
    t.add_column("Question", max_width=50)
    t.add_column("Answer", max_width=30)
    t.add_column("Source")
    t.add_column("Outcome")
    t.add_column("Type")

    for qa in pairs[:limit]:
        outcome_color = {"accepted": "green", "rejected": "red"}.get(qa["outcome"], "dim")
        t.add_row(
            qa["question_text"][:50],
            qa["answer_text"][:30],
            qa["answer_source"],
            f"[{outcome_color}]{qa['outcome']}[/{outcome_color}]",
            qa.get("field_type") or "",
        )

    console.print(t)


@qa_app.command("stats")
def qa_stats() -> None:
    """Show Q&A knowledge base statistics."""
    _bootstrap()

    from applypilot.database import get_qa_stats

    stats = get_qa_stats()
    if stats["total"] == 0:
        console.print("[dim]No Q&A pairs stored yet.[/dim]")
        return

    console.print("\n[bold]Q&A Knowledge Base Stats[/bold]\n")
    console.print(f"  Total pairs:    {stats['total']}")
    console.print(f"  Unique Qs:      {stats['unique_questions']}")

    if stats["by_source"]:
        console.print("\n  [bold]By source:[/bold]")
        for src, cnt in stats["by_source"].items():
            console.print(f"    {src}: {cnt}")

    if stats["by_outcome"]:
        console.print("\n  [bold]By outcome:[/bold]")
        for out, cnt in stats["by_outcome"].items():
            color = {"accepted": "green", "rejected": "red"}.get(out, "dim")
            console.print(f"    [{color}]{out}[/{color}]: {cnt}")

    if stats.get("by_ats"):
        console.print("\n  [bold]By ATS:[/bold]")
        for ats, cnt in stats["by_ats"].items():
            console.print(f"    {ats or 'unknown'}: {cnt}")

    console.print()


@qa_app.command("export")
def qa_export(
    output: str = typer.Option("qa_export.yaml", "--output", "-o", help="Output YAML file path."),
) -> None:
    """Export Q&A pairs to YAML for review and editing."""
    _bootstrap()

    from applypilot.database import export_qa_yaml

    content = export_qa_yaml()
    if not content:
        console.print("[dim]No Q&A pairs to export.[/dim]")
        return

    from pathlib import Path
    out_path = Path(output)
    out_path.write_text(content, encoding="utf-8")
    console.print(f"[green]Exported Q&A to:[/green] {out_path.resolve()}")


@qa_app.command("import")
def qa_import(
    file: str = typer.Argument(..., help="YAML file with Q&A pairs to import."),
) -> None:
    """Import Q&A pairs from a YAML file."""
    _bootstrap()

    from pathlib import Path
    import yaml
    from applypilot.database import store_qa

    path = Path(file)
    if not path.exists():
        console.print(f"[red]File not found: {file}[/red]")
        raise typer.Exit(code=1)

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        console.print("[red]Expected a YAML list of Q&A objects.[/red]")
        raise typer.Exit(code=1)

    count = 0
    for item in data:
        q = item.get("question", "").strip()
        a = item.get("answer", "").strip()
        if q and a:
            store_qa(
                q, a,
                source=item.get("source", "human"),
                field_type=item.get("field_type"),
                ats_slug=item.get("ats"),
            )
            count += 1

    console.print(f"[green]Imported {count} Q&A pair(s).[/green]")


# ---------------------------------------------------------------------------
# creds — site credential CRUD
# ---------------------------------------------------------------------------

creds_app = typer.Typer(name="creds", help="Manage saved site credentials (usernames / passwords).")
app.add_typer(creds_app)


@creds_app.command("list")
def creds_list(
    show: bool = typer.Option(False, "--show", "-s", help="Show passwords in plaintext."),
) -> None:
    """List all saved site credentials."""
    _bootstrap()

    from applypilot.database import get_all_accounts

    rows = get_all_accounts()
    if not rows:
        console.print("[dim]No credentials saved yet. Use [bold]applypilot creds add[/bold] to add one.[/dim]")
        return

    t = Table(title=f"Site Credentials ({len(rows)} entries)", show_header=True, header_style="bold cyan")
    t.add_column("Domain",   min_width=28)
    t.add_column("Site",     min_width=12)
    t.add_column("Email",    min_width=24)
    t.add_column("Password", min_width=16)
    t.add_column("Notes",    max_width=30)
    t.add_column("Saved",    min_width=10)

    for row in rows:
        pwd = row["password"] or ""
        pwd_display = pwd if show else (("*" * min(len(pwd), 8)) if pwd else "[dim]—[/dim]")
        saved_date = (row["created_at"] or "")[:10]
        t.add_row(
            row["domain"],
            row["site"] or "",
            row["email"],
            pwd_display,
            row["notes"] or "",
            saved_date,
        )

    console.print(t)
    if not show:
        console.print("[dim]Passwords are masked. Use [bold]--show[/bold] to reveal them.[/dim]")


@creds_app.command("show")
def creds_show(
    domain: str = typer.Argument(..., help="Domain to show credentials for (e.g. linkedin.com)."),
) -> None:
    """Show full (unmasked) credentials for a single domain."""
    _bootstrap()

    from applypilot.database import get_all_accounts

    rows = [r for r in get_all_accounts() if r["domain"] == domain]
    if not rows:
        console.print(f"[red]No credentials found for domain:[/red] {domain}")
        raise typer.Exit(code=1)

    row = rows[0]
    console.print(f"\n  [bold]Domain:[/bold]   {row['domain']}")
    console.print(f"  [bold]Site:[/bold]     {row['site'] or ''}")
    console.print(f"  [bold]Email:[/bold]    {row['email']}")
    console.print(f"  [bold]Password:[/bold] {row['password'] or '[dim](none)[/dim]'}")
    if row["notes"]:
        console.print(f"  [bold]Notes:[/bold]    {row['notes']}")
    if row["job_url"]:
        console.print(f"  [bold]Job URL:[/bold]  {row['job_url']}")
    console.print(f"  [bold]Saved:[/bold]    {(row['created_at'] or '')[:19]}\n")


@creds_app.command("add")
def creds_add(
    domain:   str = typer.Argument(..., help="Domain key (e.g. linkedin.com, myworkdayjobs.com)."),
    email:    str = typer.Option(...,  "--email",    "-e", help="Login email / username."),
    password: str = typer.Option(None, "--password", "-p", help="Password (prompted if omitted)."),
    site:     str = typer.Option(None, "--site",     "-s", help="Human-readable site name."),
    notes:    str = typer.Option(None, "--notes",    "-n", help="Optional notes."),
) -> None:
    """Add or update credentials for a site."""
    _bootstrap()

    from applypilot.database import upsert_account

    if password is None:
        password = typer.prompt(f"Password for {domain}", hide_input=True, confirmation_prompt=True)

    action = upsert_account(domain, email, password, site=site, notes=notes)
    verb = "[green]Created[/green]" if action == "created" else "[yellow]Updated[/yellow]"
    console.print(f"{verb} credentials for [bold]{domain}[/bold] ({email})")


@creds_app.command("set")
def creds_set(
    domain:   str = typer.Argument(..., help="Domain to update."),
    email:    str = typer.Option(None, "--email",    "-e", help="New email / username."),
    password: str = typer.Option(None, "--password", "-p", help="New password (prompted if --email not given either)."),
    notes:    str = typer.Option(None, "--notes",    "-n", help="Update notes."),
) -> None:
    """Update one or more fields for an existing credential entry."""
    _bootstrap()

    from applypilot.database import get_all_accounts, upsert_account

    existing = next((r for r in get_all_accounts() if r["domain"] == domain), None)
    if not existing:
        console.print(f"[red]No credentials found for:[/red] {domain}  (use [bold]add[/bold] to create one)")
        raise typer.Exit(code=1)

    new_email    = email    or existing["email"]
    new_password = password or existing["password"]
    new_notes    = notes    if notes is not None else existing["notes"]

    if not email and not password and notes is None:
        # Nothing specified — prompt for password at minimum
        new_password = typer.prompt(f"New password for {domain}", hide_input=True, confirmation_prompt=True)

    upsert_account(domain, new_email, new_password, site=existing["site"], notes=new_notes)
    console.print(f"[green]Updated[/green] credentials for [bold]{domain}[/bold]")


@creds_app.command("import-logs")
def creds_import_logs(
    log_dir: str = typer.Option(None, "--log-dir", help="Directory of apply logs. Defaults to ~/.applypilot/logs/."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be imported without writing."),
    yes:     bool = typer.Option(False, "--yes", "-y", help="Skip per-entry confirmation for free-form entries."),
) -> None:
    """Scan apply logs for account credentials and import into the DB.

    Handles both structured ACCOUNT_CREATED: lines (current format) and
    older free-form log entries where the agent wrote the password as prose.
    Already-known domains are skipped unless --yes is passed.
    """
    _bootstrap()

    import os
    from applypilot.database import mine_accounts_from_logs, upsert_account, get_all_accounts

    if log_dir is None:
        log_dir = os.path.expanduser("~/.applypilot/logs")

    console.print(f"[dim]Scanning logs in {log_dir}…[/dim]")
    found = mine_accounts_from_logs(log_dir)

    if not found:
        console.print("[dim]No credential hints found in logs.[/dim]")
        return

    existing_domains = {r["domain"] for r in get_all_accounts()}

    imported = skipped = already = 0
    for entry in found:
        domain   = entry["domain"]
        email    = entry["email"]
        password = entry.get("password", "")
        site     = entry.get("site", "")
        source   = entry.get("source", "")
        src_file = entry.get("source_file", "")
        is_new   = domain not in existing_domains

        status_tag = "[green]NEW[/green]" if is_new else "[dim]EXISTS[/dim]"
        src_tag    = "[cyan]structured[/cyan]" if source == "structured" else "[yellow]free-form[/yellow]"
        console.print(
            f"  {status_tag} {src_tag}  {domain}  {email or '[dim](no email)[/dim]'}"
            f"  pw={'***' if password else '[dim]none[/dim]'}  ({src_file})"
        )

        if not is_new:
            already += 1
            continue

        if dry_run:
            imported += 1
            continue

        # Free-form entries ask for confirmation (may be less reliable)
        if source == "free-form" and not yes:
            if not email or not password:
                console.print(f"    [dim]Skipping — missing email or password. Add manually with: "
                              f"applypilot creds add {domain}[/dim]")
                skipped += 1
                continue
            confirmed = typer.confirm(f"    Import {domain} ({email} / {password[:4]}***)?")
            if not confirmed:
                skipped += 1
                continue

        if email and password:
            upsert_account(domain, email, password, site=site or None,
                           notes=f"auto-imported from log: {src_file}")
            existing_domains.add(domain)
            imported += 1
        else:
            console.print(f"    [dim]Skipping — missing {'email' if not email else 'password'}. "
                          f"Add manually: applypilot creds add {domain}[/dim]")
            skipped += 1

    suffix = " [dim](dry run — nothing written)[/dim]" if dry_run else ""
    console.print(
        f"\n[green]Imported {imported}[/green]  "
        f"[dim]already-known {already}  skipped {skipped}[/dim]{suffix}"
    )


@creds_app.command("delete")
def creds_delete(
    domain: str = typer.Argument(..., help="Domain whose credentials to delete."),
    yes:    bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
) -> None:
    """Delete all saved credentials for a domain."""
    _bootstrap()

    from applypilot.database import delete_account, get_all_accounts

    existing = [r for r in get_all_accounts() if r["domain"] == domain]
    if not existing:
        console.print(f"[red]No credentials found for:[/red] {domain}")
        raise typer.Exit(code=1)

    row = existing[0]
    if not yes:
        confirmed = typer.confirm(f"Delete credentials for {domain} ({row['email']})?")
        if not confirmed:
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit()

    deleted = delete_account(domain)
    console.print(f"[green]Deleted {deleted} credential row(s) for[/green] [bold]{domain}[/bold]")


if __name__ == "__main__":
    app()
