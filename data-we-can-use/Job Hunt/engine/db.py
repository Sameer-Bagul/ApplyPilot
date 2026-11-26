import sqlite3
import os
import json
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "job_hunt.db"

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id TEXT UNIQUE NOT NULL,
        company_name TEXT NOT NULL,
        fit_tier TEXT NOT NULL DEFAULT 'P2',
        category TEXT,
        location_type TEXT,
        pune_cluster TEXT,
        pune_office_verified TEXT,
        india_eligible_remote TEXT,
        website TEXT,
        careers_url TEXT,
        linkedin_url TEXT,
        target_roles TEXT,
        notes TEXT,
        verified_contact_name TEXT,
        verified_contact_role TEXT,
        verified_contact_email TEXT,
        verified_contact_url TEXT,
        source_datasets TEXT,
        raw_metadata TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id TEXT UNIQUE NOT NULL,
        company_id TEXT,
        company_name TEXT NOT NULL,
        job_title TEXT NOT NULL,
        source TEXT,
        location TEXT,
        experience_req TEXT,
        salary_or_equity TEXT,
        required_skills TEXT,
        application_url TEXT,
        fit_score INTEGER DEFAULT 0,
        fit_tier TEXT DEFAULT 'Tier B',
        fit_breakdown TEXT,
        evidence_type TEXT,
        status TEXT NOT NULL DEFAULT 'Discovered',
        notes TEXT,
        posted_date TEXT,
        applied_date TEXT,
        follow_up_date TEXT,
        raw_metadata TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        contact_id TEXT UNIQUE NOT NULL,
        company_id TEXT,
        company_name TEXT NOT NULL,
        person_name TEXT NOT NULL,
        role TEXT,
        email TEXT,
        linkedin_or_source_url TEXT,
        contact_type TEXT,
        verification_status TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS daily_tracker (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT UNIQUE NOT NULL,
        target_count INTEGER DEFAULT 10,
        applied_count INTEGER DEFAULT 0,
        referrals_sent INTEGER DEFAULT 0,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_companies_tier ON companies(fit_tier);
    CREATE INDEX IF NOT EXISTS idx_companies_cluster ON companies(pune_cluster);
    CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
    CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(fit_score);
    CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts(company_id);
    """)

    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

if __name__ == "__main__":
    init_db()
