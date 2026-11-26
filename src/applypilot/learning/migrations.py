"""Database migrations and table extensions for ApplyPilot.

Provides idempotent schema creation and forward migrations for:
- ats_selector_cache (extended columns)
- hitl_tickets (extended columns for lead/job tracking)
- ats_session_vault (extended credentials)
- pattern_rules (extended fields)
- recruiter_leads (social discovery & cold mail tracking)
- career_watchlist (company career portal monitoring)
- qa_fts (SQLite FTS5 virtual table for zero-token lexical lookup)
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from pathlib import Path

from applypilot import config

logger = logging.getLogger(__name__)

AGGREGATOR_AND_ATS_DOMAINS: frozenset[str] = frozenset({
    "wellfound.com",
    "angel.co",
    "himalayas.app",
    "hirist.tech",
    "hirist.com",
    "workingnomads.com",
    "workable.com",
    "apply.workable.com",
    "smartrecruiters.com",
    "greenhouse.io",
    "boards.greenhouse.io",
    "job-boards.greenhouse.io",
    "lever.co",
    "jobs.lever.co",
    "ashbyhq.com",
    "jobs.ashbyhq.com",
    "zohorecruit.in",
    "zohorecruit.com",
    "freshteam.com",
    "keka.com",
    "param.ai",
    "careers-page.com",
    "linkedin.com",
    "in.linkedin.com",
    "cutshort.io",
    "ycombinator.com",
    "workatastartup.com",
    "djinni.co",
    "freehire.me",
    "riseflake.com",
    "tcsion.com",
    "naukri.com",
    "indeed.com",
    "bamboohr.com",
    "myworkdayjobs.com",
    "oraclecloud.com",
    "jobvite.com",
    "icims.com",
    "taleo.net",
    "recruitee.com",
    "teamtailor.com",
    "breezy.hr",
    "personio.de",
    "personio.com",
    "weworkremotely.com",
    "remoteok.com",
    "remotive.com",
    "glassdoor.com",
    "glassdoor.co.in",
    "glassdoor.com.au",
    "glassdoor.co.uk",
    "glassdoor.ca",
    "foundit.in",
    "instahyre.com",
    "internshala.com",
    "unstop.com",
    "shine.com",
    "timesjobs.com",
    "monster.com",
    "ziprecruiter.com",
    "builtin.com",
    "darwinbox.in",
    "darwinbox.com",
    "remoterocketship.com",
    "turing.com",
    "crossover.com",
    "arc.dev",
    "topstartups.io",
    "wikipedia.org",
    "en.wikipedia.org",
    "githubstatus.com",
    "startupschool.org",
    "analyticsindiamag.com",
    "topmate.io",
    "jotform.com",
    "form.jotform.com",
    "chatgpt.com",
    "chatgptexporter.com",
    "docs.google.com",
    "forms.gle",
})


def _clean_domain_token(raw: str | None) -> str:
    if not raw:
        return ""
    d = raw.strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = re.sub(r"^www\d*\.", "", d)
    d = re.split(r"[/?#]", d)[0].strip()
    d = d.split(":")[0].strip().rstrip(".")
    return d


def is_aggregator_or_ats_domain(domain_or_url: str | None) -> bool:
    """Return True if domain/URL belongs to an aggregator, job board, ATS host, or meta-platform."""
    d = _clean_domain_token(domain_or_url)
    if not d:
        return False
    if d in AGGREGATOR_AND_ATS_DOMAINS:
        return True
    return any(d.endswith("." + agg) for agg in AGGREGATOR_AND_ATS_DOMAINS)


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    """Return the set of column names currently present in a table."""
    try:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {r[1] for r in rows}
    except Exception:
        return set()


def _add_column_if_missing(
    conn: sqlite3.Connection, table_name: str, col_name: str, col_type: str
) -> bool:
    """Add a column to an existing table if it does not already exist."""
    cols = _table_columns(conn, table_name)
    if col_name not in cols:
        try:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")
            logger.info("Migrated %s: added column %s (%s)", table_name, col_name, col_type)
            return True
        except Exception as e:
            logger.warning("Could not add column %s to %s: %s", col_name, table_name, e)
    return False


def run_migrations(db_path: Path | str | sqlite3.Connection | None = None) -> sqlite3.Connection:
    """Run all schema migrations idempotently on the specified or default database.

    Creates tables if not exists, adds missing columns to existing tables,
    and initializes the FTS5 virtual table `qa_fts` for zero-token lexical search.

    Args:
        db_path: Path to the SQLite database or an active sqlite3.Connection.
                 Defaults to ~/.applypilot/applypilot.db.

    Returns:
        The sqlite3.Connection.
    """
    if isinstance(db_path, sqlite3.Connection):
        conn = db_path
    else:
        path = Path(db_path) if db_path else config.DB_PATH
        if str(path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        if str(path) != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA foreign_keys = ON")

    # 1. ats_selector_cache
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ats_selector_cache (
            selector_id          INTEGER PRIMARY KEY AUTOINCREMENT,
            cache_id             TEXT UNIQUE,
            ats_type             TEXT NOT NULL,
            domain_pattern       TEXT NOT NULL,
            step_signature       TEXT,
            page_step_signature  TEXT,
            canonical_field_id   TEXT,
            field_type           TEXT,
            css_or_aria_selector TEXT,
            playwright_locator   TEXT,
            action_type          TEXT NOT NULL,
            target_key           TEXT,
            transform_rule       TEXT,
            success_count        INTEGER DEFAULT 1,
            failure_count        INTEGER DEFAULT 0,
            confidence_score     REAL DEFAULT 1.0,
            last_verified_at     TEXT,
            created_at           TEXT
        )
    """)
    _add_column_if_missing(conn, "ats_selector_cache", "cache_id", "TEXT")
    _add_column_if_missing(conn, "ats_selector_cache", "page_step_signature", "TEXT")
    _add_column_if_missing(conn, "ats_selector_cache", "canonical_field_id", "TEXT")
    _add_column_if_missing(conn, "ats_selector_cache", "field_type", "TEXT")
    _add_column_if_missing(conn, "ats_selector_cache", "playwright_locator", "TEXT")
    _add_column_if_missing(conn, "ats_selector_cache", "transform_rule", "TEXT")
    _add_column_if_missing(conn, "ats_selector_cache", "confidence_score", "REAL DEFAULT 1.0")

    # 2. hitl_tickets
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hitl_tickets (
            ticket_id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id                    TEXT,
            lead_id                   TEXT,
            company                   TEXT,
            role_title                TEXT,
            job_url                   TEXT,
            ats_type                  TEXT,
            blocker_type              TEXT,
            questions_json            TEXT,
            dom_checkpoint_json       TEXT,
            gmail_thread_id           TEXT,
            gmail_message_id          TEXT,
            status                    TEXT NOT NULL DEFAULT 'pending_email_reply',
            unanswered_questions_json TEXT,
            created_at                TEXT,
            resolved_at               TEXT
        )
    """)
    _add_column_if_missing(conn, "hitl_tickets", "job_id", "TEXT")
    _add_column_if_missing(conn, "hitl_tickets", "lead_id", "TEXT")
    _add_column_if_missing(conn, "hitl_tickets", "company", "TEXT")
    _add_column_if_missing(conn, "hitl_tickets", "role_title", "TEXT")
    _add_column_if_missing(conn, "hitl_tickets", "ats_type", "TEXT")
    _add_column_if_missing(conn, "hitl_tickets", "blocker_type", "TEXT")
    _add_column_if_missing(conn, "hitl_tickets", "questions_json", "TEXT")

    # 3. ats_session_vault
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ats_session_vault (
            vault_id             INTEGER PRIMARY KEY AUTOINCREMENT,
            ats_type             TEXT NOT NULL,
            tenant_domain        TEXT,
            company_domain       TEXT,
            login_email          TEXT,
            account_email        TEXT,
            encrypted_password   TEXT,
            storage_state_path   TEXT,
            session_valid_until  TEXT,
            last_login_at        TEXT,
            session_valid        INTEGER DEFAULT 1,
            created_at           TEXT,
            updated_at           TEXT
        )
    """)
    _add_column_if_missing(conn, "ats_session_vault", "tenant_domain", "TEXT")
    _add_column_if_missing(conn, "ats_session_vault", "login_email", "TEXT")
    _add_column_if_missing(conn, "ats_session_vault", "encrypted_password", "TEXT")
    _add_column_if_missing(conn, "ats_session_vault", "session_valid_until", "TEXT")

    # 4. pattern_rules
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pattern_rules (
            rule_id              INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_name            TEXT UNIQUE,
            canonical_field_id   TEXT,
            label_regex          TEXT,
            regex_trigger        TEXT,
            field_type           TEXT,
            transform_expression TEXT,
            python_transform_expr TEXT,
            sample_input         TEXT,
            sample_output        TEXT,
            confidence           REAL DEFAULT 1.0,
            hit_count            INTEGER DEFAULT 0,
            created_at           TEXT
        )
    """)
    _add_column_if_missing(conn, "pattern_rules", "canonical_field_id", "TEXT")
    _add_column_if_missing(conn, "pattern_rules", "regex_trigger", "TEXT")
    _add_column_if_missing(conn, "pattern_rules", "python_transform_expr", "TEXT")
    _add_column_if_missing(conn, "pattern_rules", "sample_input", "TEXT")
    _add_column_if_missing(conn, "pattern_rules", "sample_output", "TEXT")

    # 5. recruiter_leads
    conn.execute("""
        CREATE TABLE IF NOT EXISTS recruiter_leads (
            lead_id                   TEXT PRIMARY KEY,
            job_id                    TEXT,
            company_name              TEXT,
            company_domain            TEXT,
            role_title                TEXT,
            contact_name              TEXT,
            contact_email             TEXT,
            contact_linkedin_url      TEXT,
            contact_type              TEXT,
            source_platform           TEXT,
            source_post_url           TEXT,
            evidence_snippet          TEXT,
            special_instructions_json TEXT,
            linkedin_connection_note  TEXT,
            execution_route           TEXT,
            outreach_status           TEXT DEFAULT 'queued',
            gmail_draft_id            TEXT,
            gmail_thread_id           TEXT,
            created_at                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(contact_email, role_title)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_contact_email ON recruiter_leads(contact_email)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_outreach_status ON recruiter_leads(outreach_status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_execution_route ON recruiter_leads(execution_route)")

    # Forward migration for recruiter_leads
    _add_column_if_missing(conn, "recruiter_leads", "contact_name", "TEXT")
    _add_column_if_missing(conn, "recruiter_leads", "contact_linkedin_url", "TEXT")
    _add_column_if_missing(conn, "recruiter_leads", "linkedin_connection_note", "TEXT")
    _add_column_if_missing(conn, "recruiter_leads", "email_draft_subject", "TEXT")
    _add_column_if_missing(conn, "recruiter_leads", "email_draft_body", "TEXT")
    _add_column_if_missing(conn, "recruiter_leads", "approved_at", "TIMESTAMP")
    _add_column_if_missing(conn, "recruiter_leads", "approved_by", "TEXT")
    _add_column_if_missing(conn, "recruiter_leads", "personal_email", "TEXT")
    _add_column_if_missing(conn, "recruiter_leads", "personal_email_source", "TEXT")
    _add_column_if_missing(conn, "recruiter_leads", "preferred_channel", "TEXT DEFAULT 'corporate'")

    # 6. career_watchlist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS career_watchlist (
            company_id         TEXT PRIMARY KEY,
            company_name       TEXT NOT NULL,
            slug               TEXT,
            priority_tier      INTEGER DEFAULT 2,
            is_vip             INTEGER DEFAULT 0,
            stage              TEXT,
            sector             TEXT,
            area               TEXT,
            location           TEXT,
            team_size          TEXT,
            total_funding      TEXT,
            official_domain    TEXT,
            careers_page_url   TEXT,
            ats_provider       TEXT,
            ats_board_token    TEXT,
            founders_json      TEXT,
            hr_contacts_json   TEXT,
            open_roles_count   INTEGER DEFAULT 0,
            last_checked_at    TIMESTAMP,
            last_content_hash  TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_domain ON career_watchlist(official_domain)")

    # Forward migration for career_watchlist
    _add_column_if_missing(conn, "career_watchlist", "slug", "TEXT")
    _add_column_if_missing(conn, "career_watchlist", "priority_tier", "INTEGER DEFAULT 2")
    _add_column_if_missing(conn, "career_watchlist", "is_vip", "INTEGER DEFAULT 0")
    _add_column_if_missing(conn, "career_watchlist", "stage", "TEXT")
    _add_column_if_missing(conn, "career_watchlist", "sector", "TEXT")
    _add_column_if_missing(conn, "career_watchlist", "area", "TEXT")
    _add_column_if_missing(conn, "career_watchlist", "location", "TEXT")
    _add_column_if_missing(conn, "career_watchlist", "team_size", "TEXT")
    _add_column_if_missing(conn, "career_watchlist", "total_funding", "TEXT")
    _add_column_if_missing(conn, "career_watchlist", "founders_json", "TEXT")
    _add_column_if_missing(conn, "career_watchlist", "hr_contacts_json", "TEXT")
    _add_column_if_missing(conn, "career_watchlist", "open_roles_count", "INTEGER DEFAULT 0")
    _add_column_if_missing(conn, "career_watchlist", "wikipedia_summary", "TEXT")
    _add_column_if_missing(conn, "career_watchlist", "github_org_url", "TEXT")
    _add_column_if_missing(conn, "career_watchlist", "top_projects_json", "TEXT")
    _add_column_if_missing(conn, "career_watchlist", "tech_radar_json", "TEXT")
    _add_column_if_missing(conn, "career_watchlist", "investigated_at", "TIMESTAMP")
    _add_column_if_missing(conn, "career_watchlist", "referral_available", "INTEGER DEFAULT 0")
    _add_column_if_missing(conn, "career_watchlist", "referrer_name", "TEXT")
    _add_column_if_missing(conn, "career_watchlist", "referrer_linkedin", "TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_priority ON career_watchlist(priority_tier, is_vip)")

    # Extend recruiter_leads for top-pick workflow & persona pitch
    _add_column_if_missing(conn, "recruiter_leads", "persona", "TEXT")
    _add_column_if_missing(conn, "recruiter_leads", "priority_score", "INTEGER DEFAULT 0")
    _add_column_if_missing(conn, "recruiter_leads", "email_subject", "TEXT")
    _add_column_if_missing(conn, "recruiter_leads", "email_body_text", "TEXT")
    _add_column_if_missing(conn, "recruiter_leads", "email_body_html", "TEXT")
    _add_column_if_missing(conn, "recruiter_leads", "mx_provider", "TEXT")
    _add_column_if_missing(conn, "recruiter_leads", "is_deliverable", "INTEGER DEFAULT 1")
    _add_column_if_missing(conn, "recruiter_leads", "is_catch_all", "INTEGER DEFAULT 0")
    _add_column_if_missing(conn, "recruiter_leads", "matched_job_title", "TEXT")
    _add_column_if_missing(conn, "recruiter_leads", "matched_job_url", "TEXT")
    _add_column_if_missing(conn, "recruiter_leads", "followup_draft_subject", "TEXT")
    _add_column_if_missing(conn, "recruiter_leads", "followup_draft_body", "TEXT")
    _add_column_if_missing(conn, "recruiter_leads", "dual_attack_pair_id", "TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_priority_score ON recruiter_leads(priority_score)")

    # 7. company_intel (Unified 30-day cached company research)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS company_intel (
            domain_or_name      TEXT PRIMARY KEY,
            company_name        TEXT NOT NULL,
            official_domain     TEXT,
            wikipedia_summary   TEXT,
            github_org          TEXT,
            tech_stack_json     TEXT,
            open_roles_json     TEXT,
            funding_stage       TEXT,
            ai_focus_tags       TEXT,
            key_people_json     TEXT,
            detected_email_pattern TEXT,
            email_pattern_confidence REAL,
            hiring_posts_json   TEXT,
            researched_at       TEXT NOT NULL,
            expires_at          TEXT NOT NULL
        )
    """)
    _add_column_if_missing(conn, "company_intel", "key_people_json", "TEXT")
    _add_column_if_missing(conn, "company_intel", "detected_email_pattern", "TEXT")
    _add_column_if_missing(conn, "company_intel", "email_pattern_confidence", "REAL")
    _add_column_if_missing(conn, "company_intel", "hiring_posts_json", "TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_intel_domain ON company_intel(official_domain)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_intel_expires ON company_intel(expires_at)")

    # 8. SQLite FTS5 virtual table qa_fts
    try:
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS qa_fts USING fts5(
                question_key,
                canonical_question,
                question_text,
                answer_text,
                tokenize = 'porter unicode61'
            )
        """)

        # If qa_knowledge table exists, backfill missing entries into qa_fts
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "qa_knowledge" in tables:
            # Sync any rows in qa_knowledge that aren't yet in qa_fts
            count_fts = conn.execute("SELECT count(*) FROM qa_fts").fetchone()[0]
            count_qa = conn.execute("SELECT count(*) FROM qa_knowledge").fetchone()[0]
            if count_fts == 0 and count_qa > 0:
                conn.execute("""
                    INSERT INTO qa_fts(rowid, question_key, canonical_question, question_text, answer_text)
                    SELECT id, question_key, COALESCE(canonical_question, question_key), question_text, answer_text
                    FROM qa_knowledge
                """)
    except Exception as e:
        logger.warning("FTS5 table initialization notice: %s", e)

    # 9. v4 research deduplication, discovery_sources & partial unique indexes
    v4_research_dedup_and_sources(conn)

    conn.commit()
    return conn


def _parse_json_list_safe(raw: str | None) -> list:
    if not raw:
        return []
    try:
        val = json.loads(raw)
        if isinstance(val, list):
            return val
        if isinstance(val, (dict, str)):
            return [val]
    except Exception:
        pass
    return []


def _merge_contact_lists(a_raw: str | None, b_raw: str | None) -> str | None:
    a = _parse_json_list_safe(a_raw)
    b = _parse_json_list_safe(b_raw)
    if not a and not b:
        return None
    merged = list(a)
    seen: set[tuple[str, str]] = set()
    for item in merged:
        if isinstance(item, dict):
            seen.add((str(item.get("name") or "").strip().lower(), str(item.get("email") or "").strip().lower()))
        elif isinstance(item, str):
            seen.add((item.strip().lower(), ""))
    for item in b:
        if isinstance(item, dict):
            key = (str(item.get("name") or "").strip().lower(), str(item.get("email") or "").strip().lower())
            if key not in seen and any(key):
                seen.add(key)
                merged.append(item)
        elif isinstance(item, str):
            key = (item.strip().lower(), "")
            if key not in seen and key[0]:
                seen.add(key)
                merged.append(item)
    return json.dumps(merged, ensure_ascii=False)


def _norm_company_stem(name: str | None) -> str:
    if not name:
        return ""
    s = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", name).strip()
    s = re.sub(
        r"(?i),?\s*\b(inc\.?|llc|l\.l\.c\.?|ltd\.?|limited|pvt\.?\s*ltd\.?|private\s+limited|corp\.?|corporation|gmbh|co\.?|llp|group|technologies|solutions|india|labs|payments|systems|investments)\b\.?$",
        "",
        s,
    ).strip()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _merge_watchlist_group(conn: sqlite3.Connection, rows: list[sqlite3.Row]) -> None:
    """Merge multiple career_watchlist rows into the highest-quality primary row."""
    if len(rows) <= 1:
        return

    def rank_key(r: sqlite3.Row) -> tuple:
        cname = (r["company_name"] or "").strip()
        is_noisy = 1 if ("|" in cname or ".wd" in cname.lower()) else 0
        has_cid = 0 if (r["company_id"] and str(r["company_id"]).strip()) else 1
        is_excluded = 0 if r["stage"] == "gtm_excluded" else 1
        is_vip_inv = -(r["is_vip"] or 0)
        tier = r["priority_tier"] if r["priority_tier"] is not None else 2
        has_careers = 0 if r["careers_page_url"] else 1
        return (is_noisy, has_cid, is_excluded, is_vip_inv, tier, has_careers, r["rowid"])

    ordered = sorted(rows, key=rank_key)
    primary = ordered[0]
    primary_rowid = primary["rowid"]

    merged_cid = next((r["company_id"] for r in ordered if r["company_id"] and str(r["company_id"]).strip()), None)
    merged_name = (primary["company_name"] or "").strip()
    if "|" in merged_name or ".wd" in merged_name.lower():
        clean_alt = next(
            (
                (r["company_name"] or "").strip()
                for r in ordered
                if (r["company_name"] or "").strip() and "|" not in r["company_name"] and ".wd" not in r["company_name"].lower()
            ),
            merged_name,
        )
        merged_name = clean_alt

    merged_is_vip = max((r["is_vip"] or 0) for r in ordered)
    tiers = [r["priority_tier"] for r in ordered if r["priority_tier"] is not None]
    merged_tier = min(tiers) if tiers else 2
    if any(r["stage"] == "gtm_excluded" for r in ordered):
        merged_stage = "gtm_excluded"
        merged_tier = 2
        merged_is_vip = 0
    else:
        merged_stage = next((r["stage"] for r in ordered if r["stage"]), None)

    def coalesce(field: str):
        for r in ordered:
            val = r[field]
            if val is not None and str(val).strip() != "":
                return val
        return None

    merged_founders = primary["founders_json"]
    merged_hr = primary["hr_contacts_json"]
    for r in ordered[1:]:
        merged_founders = _merge_contact_lists(merged_founders, r["founders_json"])
        merged_hr = _merge_contact_lists(merged_hr, r["hr_contacts_json"])

    merged_open_roles = max((r["open_roles_count"] or 0) for r in ordered)
    merged_referral = max((r["referral_available"] or 0) for r in ordered)

    dup_rowids = [r["rowid"] for r in ordered[1:]]
    placeholders = ",".join("?" for _ in dup_rowids)
    conn.execute(f"DELETE FROM career_watchlist WHERE rowid IN ({placeholders})", dup_rowids)

    conn.execute(
        """
        UPDATE career_watchlist
        SET company_id = COALESCE(?, company_id),
            company_name = ?,
            slug = ?,
            priority_tier = ?,
            is_vip = ?,
            stage = ?,
            sector = ?,
            area = ?,
            location = ?,
            team_size = ?,
            total_funding = ?,
            official_domain = ?,
            careers_page_url = ?,
            ats_provider = ?,
            ats_board_token = ?,
            founders_json = ?,
            hr_contacts_json = ?,
            open_roles_count = ?,
            referral_available = ?,
            referrer_name = ?,
            referrer_linkedin = ?,
            metadata_json = ?
        WHERE rowid = ?
        """,
        (
            merged_cid,
            merged_name,
            coalesce("slug"),
            merged_tier,
            merged_is_vip,
            merged_stage,
            coalesce("sector"),
            coalesce("area"),
            coalesce("location"),
            coalesce("team_size"),
            coalesce("total_funding"),
            coalesce("official_domain"),
            coalesce("careers_page_url"),
            coalesce("ats_provider"),
            coalesce("ats_board_token"),
            merged_founders,
            merged_hr,
            merged_open_roles,
            merged_referral,
            coalesce("referrer_name"),
            coalesce("referrer_linkedin"),
            coalesce("metadata_json"),
            primary_rowid,
        ),
    )


def v4_research_dedup_and_sources(conn: sqlite3.Connection) -> dict[str, int]:
    """Idempotent Phase 0 migration: clean duplicates, strip aggregator domains, create discovery_sources & unique indexes."""
    prev_factory = conn.row_factory
    conn.row_factory = sqlite3.Row
    stats = {
        "agg_domains_stripped": 0,
        "watchlist_name_groups_merged": 0,
        "watchlist_domain_groups_resolved": 0,
        "company_ids_backfilled": 0,
        "leads_agg_deleted": 0,
        "leads_dups_deleted": 0,
        "jobs_dups_deleted": 0,
    }

    try:
        # 1. Schema additions: career_watchlist.metadata_json & discovery_sources
        _add_column_if_missing(conn, "career_watchlist", "metadata_json", "TEXT")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS discovery_sources (
                url TEXT PRIMARY KEY,
                name TEXT,
                region TEXT,
                source_type TEXT,
                requires_login INTEGER DEFAULT 0,
                scope_notes TEXT,
                priority_tier INTEGER DEFAULT 2,
                last_crawled_at TEXT,
                companies_found INTEGER DEFAULT 0,
                jobs_found INTEGER DEFAULT 0
            )
        """)

        # 2. Strip aggregator/ATS/meta domains out of career_watchlist.official_domain
        dom_rows = conn.execute(
            "SELECT rowid, company_name, official_domain, careers_page_url FROM career_watchlist "
            "WHERE official_domain IS NOT NULL AND TRIM(official_domain) != ''"
        ).fetchall()
        for r in dom_rows:
            raw_dom = r["official_domain"]
            clean_dom = _clean_domain_token(raw_dom)
            cname_low = (r["company_name"] or "").strip().lower()
            is_bad_override = (
                (cname_low == "bank of america" and clean_dom == "ghr.com")
                or (cname_low == "bolt ai" and clean_dom == "bolt.earth")
            )
            if not clean_dom or is_aggregator_or_ats_domain(clean_dom) or is_bad_override:
                new_careers = r["careers_page_url"]
                if (not new_careers or str(new_careers).strip() == "") and clean_dom and "." in clean_dom and not is_bad_override:
                    raw_str = str(raw_dom).strip()
                    new_careers = raw_str if raw_str.startswith(("http://", "https://")) else f"https://{clean_dom}"
                conn.execute(
                    "UPDATE career_watchlist SET official_domain = NULL, careers_page_url = ? WHERE rowid = ?",
                    (new_careers, r["rowid"]),
                )
                stats["agg_domains_stripped"] += 1
            elif clean_dom != raw_dom:
                conn.execute(
                    "UPDATE career_watchlist SET official_domain = ? WHERE rowid = ?",
                    (clean_dom, r["rowid"]),
                )

        # 3. Merge duplicate LOWER(TRIM(company_name)) groups in career_watchlist
        name_dups = conn.execute("""
            SELECT LOWER(TRIM(company_name)) AS k, COUNT(*) AS c
            FROM career_watchlist
            GROUP BY k
            HAVING c > 1
        """).fetchall()
        for nd in name_dups:
            rows = conn.execute(
                "SELECT rowid, * FROM career_watchlist WHERE LOWER(TRIM(company_name)) = ?",
                (nd["k"],),
            ).fetchall()
            _merge_watchlist_group(conn, rows)
            stats["watchlist_name_groups_merged"] += 1

        # Trim stray leading/trailing whitespace on company_name
        conn.execute("UPDATE career_watchlist SET company_name = TRIM(company_name) WHERE company_name != TRIM(company_name)")

        # 4. Merge or disambiguate duplicate LOWER(official_domain) groups in career_watchlist
        dom_dups = conn.execute("""
            SELECT LOWER(official_domain) AS d, COUNT(*) AS c
            FROM career_watchlist
            WHERE official_domain IS NOT NULL AND official_domain != ''
            GROUP BY d
            HAVING c > 1
        """).fetchall()
        for dd in dom_dups:
            rows = conn.execute(
                "SELECT rowid, * FROM career_watchlist WHERE LOWER(official_domain) = ?",
                (dd["d"],),
            ).fetchall()
            if len(rows) <= 1:
                continue
            # Partition into same-entity aliases vs distinct sub-entities
            # Keep the highest-ranked primary row; merge rows whose stem matches/overlaps,
            # and clear official_domain on distinct sub-entities so unique index holds.
            ordered = sorted(
                rows,
                key=lambda r: (
                    1 if ("|" in (r["company_name"] or "") or ".wd" in (r["company_name"] or "").lower()) else 0,
                    0 if r["company_id"] else 1,
                    0 if r["stage"] == "gtm_excluded" else 1,
                    -(r["is_vip"] or 0),
                    r["priority_tier"] if r["priority_tier"] is not None else 2,
                    len(r["company_name"] or ""),
                    r["rowid"],
                ),
            )
            primary = ordered[0]
            p_stem = _norm_company_stem(primary["company_name"])
            same_entity = [primary]
            for other in ordered[1:]:
                o_name = (other["company_name"] or "").strip()
                o_stem = _norm_company_stem(o_name)
                if (
                    "|" in o_name
                    or ".wd" in o_name.lower()
                    or not o_stem
                    or not p_stem
                    or o_stem == p_stem
                    or (len(o_stem) >= 3 and (o_stem in p_stem or p_stem in o_stem))
                    or (o_name.lower() == "jpmc" and "jpmorgan" in (primary["company_name"] or "").lower())
                    or ("jpmorgan" in o_name.lower() and (primary["company_name"] or "").lower() == "jpmc")
                    or (o_name.lower() == "fis" and "fidelity national" in (primary["company_name"] or "").lower())
                    or ("fidelity national" in o_name.lower() and (primary["company_name"] or "").lower() == "fis")
                ):
                    same_entity.append(other)
                else:
                    conn.execute("UPDATE career_watchlist SET official_domain = NULL WHERE rowid = ?", (other["rowid"],))
            if len(same_entity) > 1:
                _merge_watchlist_group(conn, same_entity)
            stats["watchlist_domain_groups_resolved"] += 1

        # 5. Backfill missing company_id
        null_cids = conn.execute(
            "SELECT rowid FROM career_watchlist WHERE company_id IS NULL OR TRIM(company_id) = ''"
        ).fetchall()
        if null_cids:
            conn.execute("""
                UPDATE career_watchlist
                SET company_id = 'comp_' || substr(lower(hex(randomblob(5))), 1, 10)
                WHERE company_id IS NULL OR TRIM(company_id) = ''
            """)
            stats["company_ids_backfilled"] = len(null_cids)

        # Ensure Revcloud is gtm_excluded and purge meta-blacklisted rows
        conn.execute("""
            UPDATE career_watchlist
            SET stage = 'gtm_excluded', priority_tier = 2, is_vip = 0
            WHERE LOWER(TRIM(company_name)) = 'revcloud' OR LOWER(official_domain) = 'revcloud.com'
        """)
        conn.execute("""
            DELETE FROM career_watchlist
            WHERE LOWER(TRIM(company_name)) IN ('sameer bagul', 'chatgpt', 'chatgptexporter')
               OR LOWER(official_domain) IN ('chatgpt.com', 'chatgptexporter.com')
        """)

        # 6. Clean recruiter_leads (aggregator emails + duplicate emails)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        protected_lead_ids: set[str] = set()
        if "hitl_tickets" in tables:
            for r in conn.execute("SELECT DISTINCT lead_id FROM hitl_tickets WHERE lead_id IS NOT NULL").fetchall():
                protected_lead_ids.add(r[0])

        # Delete queued aggregator-domain synthesized emails
        lead_rows = conn.execute(
            "SELECT rowid, lead_id, contact_email, outreach_status FROM recruiter_leads "
            "WHERE contact_email IS NOT NULL AND TRIM(contact_email) != ''"
        ).fetchall()
        agg_lead_rowids = []
        for lr in lead_rows:
            em = lr["contact_email"].strip().lower()
            if em.endswith("@connect.linkedin.com"):
                continue
            if "@" in em:
                em_dom = em.split("@", 1)[1]
                if is_aggregator_or_ats_domain(em_dom) and lr["outreach_status"] == "queued" and lr["lead_id"] not in protected_lead_ids:
                    agg_lead_rowids.append(lr["rowid"])
        if agg_lead_rowids:
            for i in range(0, len(agg_lead_rowids), 500):
                chunk = agg_lead_rowids[i:i + 500]
                ph = ",".join("?" for _ in chunk)
                conn.execute(f"DELETE FROM recruiter_leads WHERE rowid IN ({ph})", chunk)
            stats["leads_agg_deleted"] = len(agg_lead_rowids)

        # Deduplicate recruiter_leads on LOWER(TRIM(contact_email))
        email_dups = conn.execute("""
            SELECT LOWER(TRIM(contact_email)) AS em, COUNT(*) AS c
            FROM recruiter_leads
            WHERE contact_email IS NOT NULL AND TRIM(contact_email) != ''
            GROUP BY em
            HAVING c > 1
        """).fetchall()
        for ed in email_dups:
            rows = conn.execute(
                """
                SELECT rowid, lead_id, company_name, company_domain, role_title,
                       contact_name, contact_linkedin_url, evidence_snippet,
                       matched_job_title, matched_job_url, outreach_status, priority_score
                FROM recruiter_leads
                WHERE LOWER(TRIM(contact_email)) = ?
                """,
                (ed["em"],),
            ).fetchall()
            if len(rows) <= 1:
                continue
            ordered = sorted(
                rows,
                key=lambda r: (
                    0 if r["outreach_status"] in ("sent", "approved", "drafted") else 1,
                    0 if r["lead_id"] in protected_lead_ids else 1,
                    -(r["priority_score"] or 0),
                    0 if r["contact_linkedin_url"] else 1,
                    0 if r["contact_name"] else 1,
                    r["rowid"],
                ),
            )
            keeper = ordered[0]
            keeper_id = keeper["lead_id"]
            dup_ids = [r["lead_id"] for r in ordered[1:] if r["lead_id"]]
            dup_rowids = [r["rowid"] for r in ordered[1:]]

            if "hitl_tickets" in tables and dup_ids:
                ph = ",".join("?" for _ in dup_ids)
                conn.execute(f"UPDATE hitl_tickets SET lead_id = ? WHERE lead_id IN ({ph})", [keeper_id, *dup_ids])

            def _coal(col: str):
                for r in ordered:
                    v = r[col]
                    if v is not None and str(v).strip() != "":
                        return v
                return None

            ph = ",".join("?" for _ in dup_rowids)
            conn.execute(f"DELETE FROM recruiter_leads WHERE rowid IN ({ph})", dup_rowids)
            conn.execute(
                """
                UPDATE recruiter_leads
                SET contact_email = LOWER(TRIM(contact_email)),
                    company_name = ?,
                    company_domain = ?,
                    contact_name = ?,
                    contact_linkedin_url = ?,
                    evidence_snippet = ?,
                    matched_job_title = ?,
                    matched_job_url = ?
                WHERE rowid = ?
                """,
                (
                    _coal("company_name"),
                    _coal("company_domain"),
                    _coal("contact_name"),
                    _coal("contact_linkedin_url"),
                    _coal("evidence_snippet"),
                    _coal("matched_job_title"),
                    _coal("matched_job_url"),
                    keeper["rowid"],
                ),
            )
            stats["leads_dups_deleted"] += len(dup_rowids)

        # 7. Safe historical jobs deduplication on (LOWER(TRIM(company)), LOWER(TRIM(title)), LOWER(TRIM(location)))
        if "jobs" in tables:
            protected_job_urls: set[str] = set()
            for fk_tbl, fk_col in (
                ("accounts", "job_url"),
                ("tracking_emails", "job_url"),
                ("tracking_people", "job_url"),
                ("hitl_tickets", "job_url"),
            ):
                if fk_tbl in tables:
                    for r in conn.execute(f"SELECT DISTINCT {fk_col} FROM {fk_tbl} WHERE {fk_col} IS NOT NULL").fetchall():
                        protected_job_urls.add(r[0])

            job_dup_groups = conn.execute("""
                SELECT LOWER(TRIM(company)) AS co,
                       LOWER(TRIM(title)) AS ti,
                       LOWER(TRIM(COALESCE(location, ''))) AS lo,
                       COUNT(*) AS c
                FROM jobs
                WHERE company IS NOT NULL AND TRIM(company) != ''
                  AND title IS NOT NULL AND TRIM(title) != ''
                GROUP BY co, ti, lo
                HAVING c > 1
            """).fetchall()

            safe_delete_states = {
                None, "", "discovered", "enriched", "enrich_failed",
                "low_score", "scored", "score_failed", "archived",
            }
            urls_to_delete: list[str] = []
            for jg in job_dup_groups:
                jrows = conn.execute(
                    """
                    SELECT url, state, fit_score, full_description, applied_at, discovered_at
                    FROM jobs
                    WHERE LOWER(TRIM(company)) = ?
                      AND LOWER(TRIM(title)) = ?
                      AND LOWER(TRIM(COALESCE(location, ''))) = ?
                    """,
                    (jg["co"], jg["ti"], jg["lo"]),
                ).fetchall()
                if len(jrows) <= 1:
                    continue
                ordered = sorted(
                    jrows,
                    key=lambda r: (
                        0 if r["url"] in protected_job_urls else 1,
                        0 if r["applied_at"] else 1,
                        0 if r["state"] not in safe_delete_states else 1,
                        -(r["fit_score"] if r["fit_score"] is not None else -1),
                        0 if r["full_description"] else 1,
                        -(len(r["discovered_at"] or "")),
                    ),
                )
                for loser in ordered[1:]:
                    if (
                        loser["url"] not in protected_job_urls
                        and not loser["applied_at"]
                        and loser["state"] in safe_delete_states
                    ):
                        urls_to_delete.append(loser["url"])

            if urls_to_delete:
                for i in range(0, len(urls_to_delete), 400):
                    chunk = urls_to_delete[i:i + 400]
                    ph = ",".join("?" for _ in chunk)
                    if "job_state_transitions" in tables:
                        conn.execute(f"DELETE FROM job_state_transitions WHERE job_url IN ({ph})", chunk)
                    conn.execute(f"DELETE FROM jobs WHERE url IN ({ph})", chunk)
                stats["jobs_dups_deleted"] = len(urls_to_delete)

        # 8. Partial unique indexes preventing future domain & email duplicates
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_watchlist_unique_domain
              ON career_watchlist(LOWER(official_domain))
              WHERE official_domain IS NOT NULL AND official_domain != ''
        """)
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_unique_email
              ON recruiter_leads(LOWER(contact_email))
              WHERE contact_email IS NOT NULL AND contact_email != ''
        """)

        conn.commit()
    finally:
        conn.row_factory = prev_factory

    return stats
