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

import logging
import sqlite3
from pathlib import Path

from applypilot import config

logger = logging.getLogger(__name__)


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
    conn.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_priority ON career_watchlist(priority_tier, is_vip)")

    # Ensure jobs table has execution_route
    if "jobs" in {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}:
        _add_column_if_missing(conn, "jobs", "execution_route", "TEXT")

    # 7. SQLite FTS5 virtual table qa_fts
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

    conn.commit()
    return conn
