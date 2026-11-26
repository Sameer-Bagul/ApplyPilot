#!/usr/bin/env python3
"""Unified High-Scale Data Ingestion Pipeline for ApplyPilot.

Ingests, normalizes, deduplicates, and synchronizes:
1. Career Watchlist (Tavilo Prospect Master + Job Hunt Master Database)
2. Recruiter Leads (Tavilo Decision-Makers & Secondary Contacts + LinkedIn Inbound Recruiter Messages)
3. Curated, Saved, and Submitted Job Applications (Master Jobs Database + LinkedIn Historical Export)
4. Screening Q&A Knowledge & Full-Text Search (LinkedIn Screening Responses + Application Q&A Blocks)
5. LinkedIn Connections Hook (Prepared for Connections.csv)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ApplyPilot imports
from applypilot.config import DB_PATH
from applypilot.database import (
    commit_with_retry,
    get_connection,
    init_db,
    normalize_question,
    question_key,
)
from applypilot.learning.migrations import run_migrations

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("applypilot.ingestion")

DEFAULT_DATA_DIR = Path("/home/sameer/Projects/ApplyPilot/data-we-can-use")

# Generic email prefixes for corporate vs personal routing
GENERIC_EMAIL_PREFIXES = (
    "info@",
    "sales@",
    "support@",
    "contact@",
    "hello@",
    "help@",
    "team@",
    "jobs@",
    "careers@",
    "admin@",
    "office@",
    "inquiries@",
    "press@",
    "biz@",
    "hi@",
    "marketing@",
    "billing@",
    "general@",
    "connect@",
    "inquiry@",
    "service@",
    "hr@",
    "recruit@",
    "recruiting@",
    "talent@",
    "payments@",
    "operations@",
    "privacy@",
    "media@",
)


# ==============================================================================
# Helper Normalizers & Profile Resolvers
# ==============================================================================

def normalize_company_name(name: str) -> str:
    """Normalize company name by stripping legal suffixes, aliases, and trailing punctuation."""
    if not name:
        return ""
    # Strip parenthesized or bracketed parts: e.g. "Simple Biz (Simple.biz)" -> "Simple Biz"
    s = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", name).strip()
    # Strip legal entity suffixes
    pattern = (
        r"(?i),?\s*\b("
        r"inc\.?|llc|l\.l\.c\.?|ltd\.?|limited|pvt\.?\s*ltd\.?|"
        r"private\s+limited|corp\.?|corporation|gmbh|co\.?|llp"
        r")\b\.?$"
    )
    s = re.sub(pattern, "", s).strip()
    # Strip trailing punctuation, dashes, commas, dots
    s = re.sub(r"[\s,\.-]+$", "", s).strip()
    return s


def canonicalize_domain(url_or_domain: str) -> str:
    """Canonicalize a website or domain string by removing protocol, www, path, query, and port."""
    if not url_or_domain:
        return ""
    d = url_or_domain.strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = re.sub(r"^www\.", "", d)
    # Strip path, query, fragment
    d = re.split(r"[/?#]", d)[0].strip()
    # Strip port
    d = d.split(":")[0].strip()
    return d


def is_generic_email(email: str) -> bool:
    """Return True if email starts with a common corporate/support prefix."""
    em = email.lower().strip()
    return any(em.startswith(prefix) for prefix in GENERIC_EMAIL_PREFIXES)


def make_synthetic_email(name: str, company: str, salt: str = "") -> str:
    """Generate a clean synthetic email for LinkedIn-only decision-makers."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    h = hashlib.sha256((name + company + salt).encode("utf-8")).hexdigest()[:8]
    return f"linkedin-{slug}-{h}@connect.linkedin.com"


def parse_json_list(raw: Optional[str]) -> List[Any]:
    """Safely parse JSON contact lists, handling malformed data or raw dicts/strings."""
    if not raw:
        return []
    try:
        val = json.loads(raw)
        if isinstance(val, list):
            return val
        elif isinstance(val, (dict, str)):
            return [val]
        return []
    except Exception:
        return []


def contact_name_match(existing_list: List[Any], name: str) -> bool:
    """Check if a contact name or email already exists in a mixed string/dict contact list."""
    if not name:
        return False
    target = name.strip().lower()
    for item in existing_list:
        if isinstance(item, dict):
            c_name = str(item.get("name") or "").strip().lower()
            c_email = str(item.get("email") or "").strip().lower()
            if target in (c_name, c_email):
                return True
        elif isinstance(item, str):
            if item.strip().lower() == target:
                return True
    return False


def load_profile_fallbacks(data_dir: Path) -> Dict[str, str]:
    """Load default/profile answers for standard application screening fields from LinkedIn export."""
    defaults = {
        "First name": "Sameer",
        "Last name": "Bagul",
        "City": "Pune",
        "Location (city)": "Pune",
        "State / Province": "Maharashtra",
        "Country": "India",
        "Degree": "Bachelor of Engineering - BE",
        "School": "Savitribai Phule Pune University",
        "Major / Field of study": "Information Technology",
        "Company": "Revcloud",
        "Your title": "Artificial Intelligence Engineer",
        "Description": "AI Engineer building production LLM, RAG and Agentic systems",
    }
    profile_path = data_dir / "my linkedin data" / "Profile.csv"
    if profile_path.exists():
        try:
            with open(profile_path, "r", encoding="utf-8-sig", errors="replace") as f:
                rows = list(csv.DictReader(f))
                if rows:
                    p = rows[0]
                    if p.get("First Name"):
                        defaults["First name"] = p["First Name"].strip()
                    if p.get("Last Name"):
                        defaults["Last name"] = p["Last Name"].strip()
                    if p.get("Geo Location"):
                        loc = p["Geo Location"].strip()
                        if "Pune" in loc:
                            defaults["City"] = "Pune"
                            defaults["Location (city)"] = "Pune"
                            defaults["State / Province"] = "Maharashtra"
                            defaults["Country"] = "India"
        except Exception as e:
            logger.debug("Profile fallback parse notice: %s", e)

    edu_path = data_dir / "my linkedin data" / "Education.csv"
    if edu_path.exists():
        try:
            with open(edu_path, "r", encoding="utf-8-sig", errors="replace") as f:
                rows = list(csv.DictReader(f))
                if rows:
                    ed = rows[0]
                    if ed.get("School Name"):
                        defaults["School"] = ed["School Name"].strip()
                    if ed.get("Degree Name"):
                        defaults["Degree"] = ed["Degree Name"].strip()
        except Exception as e:
            logger.debug("Education fallback parse notice: %s", e)

    return defaults


# ==============================================================================
# 1. Career Watchlist Ingestion
# ==============================================================================

def ingest_career_watchlist(
    conn: sqlite3.Connection,
    data_dir: Path = DEFAULT_DATA_DIR,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Ingest, normalize, deduplicate, and tier companies from Tavilo and Job Hunt into career_watchlist."""
    logger.info("--- Starting Career Watchlist Ingestion ---")

    # Load existing companies from DB for deduplication and consolidation
    existing_rows = conn.execute(
        "SELECT rowid, company_id, company_name, official_domain, priority_tier, is_vip, stage, "
        "       founders_json, hr_contacts_json, area, location, careers_page_url, "
        "       ats_provider, ats_board_token, sector, team_size, open_roles_count "
        "FROM career_watchlist"
    ).fetchall()

    company_records: Dict[str, Dict[str, Any]] = {}
    name_to_cid: Dict[str, str] = {}
    domain_to_cid: Dict[str, str] = {}
    duplicate_rowids_to_remove: Set[int] = set()

    for row in existing_rows:
        row_id = row[0]
        cid = row[1]
        cname = row[2]
        cdom = canonicalize_domain(row[3])
        norm_n = normalize_company_name(cname).lower()

        # Check if this company already loaded from an earlier duplicate row in DB
        primary_cid: Optional[str] = None
        if cdom and cdom in domain_to_cid:
            primary_cid = domain_to_cid[cdom]
        elif norm_n and norm_n in name_to_cid:
            primary_cid = name_to_cid[norm_n]

        if primary_cid and primary_cid in company_records:
            # Consolidate duplicate into primary_cid
            prim = company_records[primary_cid]
            duplicate_rowids_to_remove.add(row_id)
            if not prim["official_domain"] and cdom:
                prim["official_domain"] = cdom
                domain_to_cid[cdom] = primary_cid
            if not prim["careers_page_url"] and row[11]:
                prim["careers_page_url"] = row[11]
            if not prim["ats_provider"] and row[12]:
                prim["ats_provider"] = row[12]
            if not prim["ats_board_token"] and row[13]:
                prim["ats_board_token"] = row[13]
            if not prim["sector"] and row[14]:
                prim["sector"] = row[14]
            if not prim["team_size"] and row[15]:
                prim["team_size"] = row[15]
            prim["open_roles_count"] = max(prim.get("open_roles_count", 0), row[16] or 0)
            for f in parse_json_list(row[7]):
                if isinstance(f, dict) and f.get("name") and not contact_name_match(prim["founders"], f["name"]):
                    prim["founders"].append(f)
            for h in parse_json_list(row[8]):
                if isinstance(h, dict) and h.get("name") and not contact_name_match(prim["hr_contacts"], h["name"]):
                    prim["hr_contacts"].append(h)
            continue

        # If existing row had a NULL company_id, generate a valid company_id and prune old rowid
        if not cid:
            cid = f"comp_{uuid.uuid4().hex[:10]}"
            duplicate_rowids_to_remove.add(row_id)

        company_records[cid] = {
            "company_id": cid,
            "company_name": cname,
            "official_domain": cdom or None,
            "priority_tier": row[4] if row[4] is not None else 2,
            "is_vip": row[5] if row[5] is not None else 0,
            "stage": row[6],
            "founders": parse_json_list(row[7]),
            "hr_contacts": parse_json_list(row[8]),
            "area": row[9],
            "location": row[10],
            "careers_page_url": row[11],
            "ats_provider": row[12],
            "ats_board_token": row[13],
            "sector": row[14],
            "team_size": row[15],
            "open_roles_count": row[16] or 0,
            "is_existing": True,
        }
        if norm_n:
            name_to_cid[norm_n] = cid
        if cdom:
            domain_to_cid[cdom] = cid

    initial_count = len(existing_rows)
    logger.info(
        "Loaded %d existing companies from career_watchlist (%d consolidated into primary records)",
        initial_count, len(duplicate_rowids_to_remove),
    )

    def resolve_or_create_company(raw_name: str, raw_domain: str) -> Tuple[str, bool]:
        norm_n = normalize_company_name(raw_name).lower()
        canon_d = canonicalize_domain(raw_domain)
        # Check by domain first
        if canon_d and canon_d in domain_to_cid:
            cid = domain_to_cid[canon_d]
            if norm_n and norm_n not in name_to_cid:
                name_to_cid[norm_n] = cid
            return cid, False
        # Check by normalized name
        if norm_n and norm_n in name_to_cid:
            cid = name_to_cid[norm_n]
            if canon_d and canon_d not in domain_to_cid:
                domain_to_cid[canon_d] = cid
                if not company_records[cid]["official_domain"]:
                    company_records[cid]["official_domain"] = canon_d
            return cid, False
        # Create new
        new_cid = f"comp_{uuid.uuid4().hex[:10]}"
        company_records[new_cid] = {
            "company_id": new_cid,
            "company_name": raw_name.strip(),
            "official_domain": canon_d or None,
            "priority_tier": 2,
            "is_vip": 0,
            "stage": None,
            "founders": [],
            "hr_contacts": [],
            "area": None,
            "location": None,
            "careers_page_url": None,
            "ats_provider": None,
            "ats_board_token": None,
            "sector": None,
            "team_size": None,
            "open_roles_count": 0,
            "is_existing": False,
        }
        if norm_n:
            name_to_cid[norm_n] = new_cid
        if canon_d:
            domain_to_cid[canon_d] = new_cid
        return new_cid, True

    # 1. Parse Tavilo Start Here (VIP / Tier 1: 501 companies)
    start_here_path = data_dir / "tavilo-data" / "Tavilo prospect list - Prospects - start here.csv"
    tavilo_start_here_cids: Set[str] = set()
    if start_here_path.exists():
        with open(start_here_path, "r", encoding="utf-8-sig", errors="replace") as f:
            for r in csv.DictReader(f):
                cname = r.get("Company", "").strip()
                cdom = r.get("Website", "").strip()
                if not cname:
                    continue
                cid, _ = resolve_or_create_company(cname, cdom)
                tavilo_start_here_cids.add(cid)
                rec = company_records[cid]
                rec["priority_tier"] = 1
                rec["is_vip"] = 1
        logger.info("Processed Tavilo Start Here: %d companies flagged VIP/Tier 1", len(tavilo_start_here_cids))

    # 2. Parse Tavilo Do Not Target (623 companies -> Priority Tier 2, stage='gtm_excluded')
    dnt_path = data_dir / "tavilo-data" / "Tavilo prospect list - Do not target.csv"
    tavilo_dnt_cids: Set[str] = set()
    if dnt_path.exists():
        with open(dnt_path, "r", encoding="utf-8-sig", errors="replace") as f:
            for r in csv.DictReader(f):
                cname = r.get("company_name", "").strip()
                cdom = r.get("company_domain", "").strip()
                if not cname:
                    continue
                cid, _ = resolve_or_create_company(cname, cdom)
                tavilo_dnt_cids.add(cid)
                rec = company_records[cid]
                rec["stage"] = "gtm_excluded"
                rec["priority_tier"] = 2
                rec["is_vip"] = 0
        logger.info("Processed Tavilo Do Not Target: %d companies recorded", len(tavilo_dnt_cids))

    # 3. Parse Tavilo Needs Validation (Tier 3)
    needs_val_path = data_dir / "tavilo-data" / "Tavilo prospect list - Needs validation.csv"
    tavilo_needs_val_cids: Set[str] = set()
    if needs_val_path.exists():
        with open(needs_val_path, "r", encoding="utf-8-sig", errors="replace") as f:
            for r in csv.DictReader(f):
                cname = r.get("company_name", "").strip()
                cdom = r.get("company_domain", "").strip()
                if not cname:
                    continue
                cid, _ = resolve_or_create_company(cname, cdom)
                tavilo_needs_val_cids.add(cid)
                rec = company_records[cid]
                if cid not in tavilo_start_here_cids and cid not in tavilo_dnt_cids:
                    rec["priority_tier"] = 3
                    rec["is_vip"] = 0
        logger.info("Processed Tavilo Needs Validation: %d companies", len(tavilo_needs_val_cids))

    # 4. Parse Job Hunt Master Database (2,056 tech companies)
    jh_companies_path = data_dir / "Job Hunt" / "data" / "master_companies_database.csv"
    jh_count = 0
    if jh_companies_path.exists():
        with open(jh_companies_path, "r", encoding="utf-8-sig", errors="replace") as f:
            for r in csv.DictReader(f):
                cname = r.get("Company Name", "").strip()
                cdom = r.get("Website", "").strip()
                if not cname:
                    continue
                cid, _ = resolve_or_create_company(cname, cdom)
                jh_count += 1
                rec = company_records[cid]
                fit_tier = r.get("Fit Tier", "").strip().upper()

                # Tiering (do not alter if in tavilo_dnt_cids)
                if cid not in tavilo_dnt_cids:
                    if fit_tier == "P1":
                        rec["priority_tier"] = 1
                        rec["is_vip"] = 1
                    elif fit_tier == "P3" and rec["priority_tier"] != 1:
                        rec["priority_tier"] = 3
                        rec["is_vip"] = 0
                    elif fit_tier == "P2" and rec["priority_tier"] != 1:
                        rec["priority_tier"] = 2
                        rec["is_vip"] = 0

                # Micro-clusters and location
                pune_cluster = r.get("Pune Cluster", "").strip()
                location_type = r.get("Location Type", "").strip()
                category = r.get("Category", "").strip()
                careers_url = r.get("Careers URL", "").strip()

                if pune_cluster and not rec["area"]:
                    rec["area"] = pune_cluster
                if location_type and not rec["location"]:
                    rec["location"] = location_type
                if category and not rec["sector"]:
                    rec["sector"] = category
                if careers_url and not rec["careers_page_url"]:
                    rec["careers_page_url"] = careers_url

                # Contact info in row
                contact_name = r.get("Verified Contact Name", "").strip()
                contact_role = r.get("Verified Contact Role", "").strip()
                contact_email = r.get("Verified Contact Email", "").strip()
                contact_link = r.get("Verified Contact Link", "").strip()

                if contact_name:
                    c_entry = {
                        "name": contact_name,
                        "title": contact_role,
                        "email": contact_email,
                        "linkedin": contact_link,
                    }
                    role_lower = contact_role.lower()
                    if any(w in role_lower for w in ["founder", "ceo", "cto", "co-founder"]):
                        if not contact_name_match(rec["founders"], contact_name):
                            rec["founders"].append(c_entry)
                    else:
                        if not contact_name_match(rec["hr_contacts"], contact_name):
                            rec["hr_contacts"].append(c_entry)

        logger.info("Processed Job Hunt Master: %d rows", jh_count)

    # 5. Parse Tavilo Master (all rows) (2,290 rows)
    tavilo_master_path = data_dir / "tavilo-data" / "Tavilo prospect list - Master (all rows).csv"
    tav_master_count = 0
    if tavilo_master_path.exists():
        with open(tavilo_master_path, "r", encoding="utf-8-sig", errors="replace") as f:
            for r in csv.DictReader(f):
                cname = r.get("company_name", "").strip()
                cdom = r.get("company_domain", "").strip()
                if not cname:
                    continue
                cid, _ = resolve_or_create_company(cname, cdom)
                tav_master_count += 1
                rec = company_records[cid]

                if not rec["sector"] and r.get("industry"):
                    rec["sector"] = r.get("industry").strip()
                if not rec["team_size"] and r.get("employee_count"):
                    rec["team_size"] = r.get("employee_count").strip()

                # Extract Decision Maker
                dm_name = r.get("decision_maker", "").strip()
                dm_title = r.get("decision_maker_title", "").strip()
                dm_li = r.get("decision_maker_linkedin", "").strip()
                public_email = r.get("public_email", "").strip()

                if dm_name:
                    dm_entry = {
                        "name": dm_name,
                        "title": dm_title,
                        "email": public_email,
                        "linkedin": dm_li,
                    }
                    if not contact_name_match(rec["founders"], dm_name):
                        rec["founders"].append(dm_entry)

                # Extract Secondary Contact
                sec_name = r.get("second_contact", "").strip()
                sec_title = r.get("second_contact_title", "").strip()
                sec_li = r.get("second_contact_linkedin", "").strip()
                if sec_name:
                    sec_entry = {
                        "name": sec_name,
                        "title": sec_title,
                        "email": "",
                        "linkedin": sec_li,
                    }
                    if not contact_name_match(rec["hr_contacts"], sec_name):
                        rec["hr_contacts"].append(sec_entry)

        logger.info("Processed Tavilo Master (all rows): %d rows", tav_master_count)

    # 6. Parse Job Hunt Contacts (103 contacts)
    jh_contacts_path = data_dir / "Job Hunt" / "data" / "master_contacts_database.csv"
    if jh_contacts_path.exists():
        with open(jh_contacts_path, "r", encoding="utf-8-sig", errors="replace") as f:
            for r in csv.DictReader(f):
                cname = r.get("company_name", "").strip()
                pname = r.get("person_name", "").strip()
                prole = r.get("role", "").strip()
                pemail = r.get("email", "").strip()
                plink = r.get("linkedin_or_source_url", "").strip()
                ctype = r.get("contact_type", "").strip().lower()
                if not cname or not pname:
                    continue
                cid, _ = resolve_or_create_company(cname, "")
                rec = company_records[cid]
                entry = {
                    "name": pname,
                    "title": prole,
                    "email": pemail,
                    "linkedin": plink,
                }
                if "founder" in ctype:
                    if not contact_name_match(rec["founders"], pname):
                        rec["founders"].append(entry)
                else:
                    if not contact_name_match(rec["hr_contacts"], pname):
                        rec["hr_contacts"].append(entry)

    # MANDATORY RULE: Enforce that all Tavilo Do Not Target companies are priority_tier=2, is_vip=0, stage='gtm_excluded'
    for cid in tavilo_dnt_cids:
        if cid in company_records:
            rec = company_records[cid]
            rec["priority_tier"] = 2
            rec["is_vip"] = 0
            rec["stage"] = "gtm_excluded"

    # Write / Upsert to Database
    total_records = len(company_records)
    net_new_count = sum(1 for rec in company_records.values() if not rec["is_existing"])
    tier1_vip_count = sum(1 for rec in company_records.values() if rec["is_vip"] == 1 or rec["priority_tier"] == 1)
    tier2_count = sum(1 for rec in company_records.values() if rec["priority_tier"] == 2 and rec["is_vip"] == 0)
    tier3_count = sum(1 for rec in company_records.values() if rec["priority_tier"] == 3)
    gtm_excluded_count = sum(1 for rec in company_records.values() if rec["stage"] == "gtm_excluded")

    logger.info(
        "Career Watchlist Summary: %d total (%d net-new, %d existing). T1 VIP: %d, T2: %d, T3: %d, GTM Excluded: %d",
        total_records, net_new_count, len(existing_rows) - len(duplicate_rowids_to_remove),
        tier1_vip_count, tier2_count, tier3_count, gtm_excluded_count,
    )

    if not dry_run:
        now_iso = datetime.now(timezone.utc).isoformat()
        cursor = conn.cursor()

        # Delete consolidated duplicate and null-ID rowids
        if duplicate_rowids_to_remove:
            cursor.executemany(
                "DELETE FROM career_watchlist WHERE rowid = ?",
                [(r,) for r in duplicate_rowids_to_remove],
            )
            logger.info("Pruned %d duplicate/null-ID company records from career_watchlist", len(duplicate_rowids_to_remove))

        for rec in company_records.values():
            founders_str = json.dumps(rec["founders"], ensure_ascii=False) if rec["founders"] else None
            hr_str = json.dumps(rec["hr_contacts"], ensure_ascii=False) if rec["hr_contacts"] else None
            cursor.execute(
                """
                INSERT INTO career_watchlist (
                    company_id, company_name, official_domain, careers_page_url,
                    ats_provider, ats_board_token, priority_tier, is_vip, stage,
                    sector, area, location, team_size, founders_json, hr_contacts_json,
                    open_roles_count, last_checked_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(company_id) DO UPDATE SET
                    company_name = excluded.company_name,
                    official_domain = COALESCE(excluded.official_domain, career_watchlist.official_domain),
                    careers_page_url = COALESCE(excluded.careers_page_url, career_watchlist.careers_page_url),
                    ats_provider = COALESCE(excluded.ats_provider, career_watchlist.ats_provider),
                    ats_board_token = COALESCE(excluded.ats_board_token, career_watchlist.ats_board_token),
                    priority_tier = excluded.priority_tier,
                    is_vip = excluded.is_vip,
                    stage = COALESCE(excluded.stage, career_watchlist.stage),
                    sector = COALESCE(excluded.sector, career_watchlist.sector),
                    area = COALESCE(excluded.area, career_watchlist.area),
                    location = COALESCE(excluded.location, career_watchlist.location),
                    team_size = COALESCE(excluded.team_size, career_watchlist.team_size),
                    founders_json = COALESCE(excluded.founders_json, career_watchlist.founders_json),
                    hr_contacts_json = COALESCE(excluded.hr_contacts_json, career_watchlist.hr_contacts_json),
                    open_roles_count = MAX(excluded.open_roles_count, career_watchlist.open_roles_count),
                    last_checked_at = excluded.last_checked_at
                """,
                (
                    rec["company_id"],
                    rec["company_name"],
                    rec["official_domain"],
                    rec["careers_page_url"],
                    rec["ats_provider"],
                    rec["ats_board_token"],
                    rec["priority_tier"],
                    rec["is_vip"],
                    rec["stage"],
                    rec["sector"],
                    rec["area"],
                    rec["location"],
                    rec["team_size"],
                    founders_str,
                    hr_str,
                    rec["open_roles_count"],
                    now_iso,
                ),
            )

    return {
        "initial_count": initial_count,
        "total_records": total_records,
        "net_new": net_new_count,
        "tier1_vip": tier1_vip_count,
        "tier2": tier2_count,
        "tier3": tier3_count,
        "gtm_excluded": gtm_excluded_count,
        "pruned_duplicates": len(duplicate_rowids_to_remove),
    }


# ==============================================================================
# 2. Recruiter Leads Ingestion
# ==============================================================================

def ingest_recruiter_leads(
    conn: sqlite3.Connection,
    data_dir: Path = DEFAULT_DATA_DIR,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Ingest decision-makers, secondary contacts, and inbound recruiter messages into recruiter_leads."""
    logger.info("--- Starting Recruiter Leads Ingestion ---")

    initial_count = conn.execute("SELECT COUNT(*) FROM recruiter_leads").fetchone()[0]
    logger.info("Current recruiter_leads count: %d", initial_count)

    tavilo_master_path = data_dir / "tavilo-data" / "Tavilo prospect list - Master (all rows).csv"
    leads_to_ingest: List[Dict[str, Any]] = []
    seen_pairs: Set[Tuple[str, str]] = set()

    personal_email_count = 0
    corporate_email_count = 0
    linkedin_only_count = 0
    total_dms_processed = 0
    total_secs_processed = 0

    if tavilo_master_path.exists():
        with open(tavilo_master_path, "r", encoding="utf-8-sig", errors="replace") as f:
            reader = list(csv.DictReader(f))

        for idx, r in enumerate(reader):
            comp_name = r.get("company_name", "").strip()
            comp_dom = canonicalize_domain(r.get("company_domain", ""))
            evidence = r.get("evidence_summary", "").strip()
            pitch_angle = r.get("pitch_angle", "").strip()
            priority_score_raw = r.get("Tavilo_priority_score", "").strip()
            priority_score = int(priority_score_raw) if priority_score_raw.isdigit() else 80

            spec_json = json.dumps({
                "pitch_angle": pitch_angle,
                "evidence_type": r.get("evidence_type", ""),
                "competitor_vendor": r.get("competitor_vendor", ""),
            }, ensure_ascii=False)

            # Extracted public email(s) in row
            public_email = r.get("public_email", "").strip()
            extracted_emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", public_email)

            # 1. Decision Maker (816 in Tavilo)
            dm_name = r.get("decision_maker", "").strip()
            dm_title = r.get("decision_maker_title", "").strip() or "Executive Decision Maker"
            dm_li = r.get("decision_maker_linkedin", "").strip()

            if dm_name:
                total_dms_processed += 1
                contact_email: str
                route: str
                channel: str
                personal_em_val: Optional[str] = None

                if dm_li:
                    # Exactly 342 decision-makers have LinkedIn profiles -> synthetic email + LINKEDIN_ONLY
                    contact_email = make_synthetic_email(dm_name, comp_name, salt=f"dm_{idx}")
                    route = "LINKEDIN_ONLY"
                    channel = "linkedin"
                    linkedin_only_count += 1
                    if extracted_emails and not is_generic_email(extracted_emails[0]):
                        personal_em_val = extracted_emails[0].lower().strip()
                elif extracted_emails:
                    contact_email = extracted_emails[0].lower().strip()
                    route = "EMAIL"
                    if is_generic_email(contact_email):
                        channel = "corporate"
                        corporate_email_count += 1
                    else:
                        channel = "personal"
                        personal_email_count += 1
                        personal_em_val = contact_email
                else:
                    contact_email = make_synthetic_email(dm_name, comp_name, salt=f"dm_{idx}")
                    route = "RESEARCH_NEEDED"
                    channel = "corporate"

                persona = "founder" if any(w in dm_title.lower() for w in ["founder", "ceo", "owner", "cto", "co-founder"]) else "executive"
                pair = (contact_email, dm_title)
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    leads_to_ingest.append({
                        "lead_id": f"lead_{uuid.uuid4().hex[:12]}",
                        "company_name": comp_name,
                        "company_domain": comp_dom,
                        "role_title": dm_title,
                        "contact_name": dm_name,
                        "contact_email": contact_email,
                        "contact_linkedin_url": dm_li or None,
                        "contact_type": "decision_maker",
                        "source_platform": "tavilo_master",
                        "evidence_snippet": evidence,
                        "special_instructions_json": spec_json,
                        "execution_route": route,
                        "outreach_status": "queued",
                        "preferred_channel": channel,
                        "persona": persona,
                        "priority_score": priority_score,
                        "personal_email": personal_em_val,
                    })

            # 2. Secondary Contact (456 in Tavilo)
            sec_name = r.get("second_contact", "").strip()
            sec_title = r.get("second_contact_title", "").strip() or "Secondary Leadership Contact"
            sec_li = r.get("second_contact_linkedin", "").strip()

            if sec_name:
                total_secs_processed += 1
                sec_email: str
                sec_route: str
                sec_channel: str
                sec_personal_val: Optional[str] = None

                if sec_li:
                    sec_email = make_synthetic_email(sec_name, comp_name, salt=f"sec_{idx}")
                    sec_route = "LINKEDIN_ONLY"
                    sec_channel = "linkedin"
                elif len(extracted_emails) > 1:
                    sec_email = extracted_emails[1].lower().strip()
                    sec_route = "EMAIL"
                    if is_generic_email(sec_email):
                        sec_channel = "corporate"
                        corporate_email_count += 1
                    else:
                        sec_channel = "personal"
                        personal_email_count += 1
                        sec_personal_val = sec_email
                elif extracted_emails and dm_li:
                    # DM was routed via LinkedIn, so public email is available for secondary contact
                    sec_email = extracted_emails[0].lower().strip()
                    sec_route = "EMAIL"
                    if is_generic_email(sec_email):
                        sec_channel = "corporate"
                        corporate_email_count += 1
                    else:
                        sec_channel = "personal"
                        personal_email_count += 1
                        sec_personal_val = sec_email
                else:
                    sec_email = make_synthetic_email(sec_name, comp_name, salt=f"sec_{idx}")
                    sec_route = "RESEARCH_NEEDED"
                    sec_channel = "corporate"

                sec_persona = "talent_acquisition" if any(w in sec_title.lower() for w in ["hr", "recruiter", "talent", "people"]) else "executive"
                pair = (sec_email, sec_title)
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    leads_to_ingest.append({
                        "lead_id": f"lead_{uuid.uuid4().hex[:12]}",
                        "company_name": comp_name,
                        "company_domain": comp_dom,
                        "role_title": sec_title,
                        "contact_name": sec_name,
                        "contact_email": sec_email,
                        "contact_linkedin_url": sec_li or None,
                        "contact_type": "secondary_contact",
                        "source_platform": "tavilo_master",
                        "evidence_snippet": evidence,
                        "special_instructions_json": spec_json,
                        "execution_route": sec_route,
                        "outreach_status": "queued",
                        "preferred_channel": sec_channel,
                        "persona": sec_persona,
                        "priority_score": max(50, priority_score - 10),
                        "personal_email": sec_personal_val,
                    })

    # 3. Ingest 5 Verified Recruiter Inbound Messages from messages.csv
    recruiter_messages = [
        {
            "name": "Gandharva Hardikar",
            "email": "gandharva.hardikar@gmail.com",
            "role": "Senior Tech / Engineering Contact",
            "company": "Hardikar Tech",
            "domain": "gmail.com",
            "linkedin": "https://www.linkedin.com/in/gandharvahardikar",
            "channel": "personal",
            "route": "EMAIL",
            "evidence": "LinkedIn messaging thread: 'Oh I would be glad to explore My Email - gandharva.hardikar@gmail.com'",
        },
        {
            "name": "Kartik Shete",
            "email": "jobs@starkdigital.net",
            "role": "Technical Recruiter",
            "company": "Stark Digital",
            "domain": "starkdigital.net",
            "linkedin": "https://www.linkedin.com/in/kartik-shete",
            "channel": "corporate",
            "route": "EMAIL",
            "evidence": "LinkedIn messaging thread: 'Please send resume to jobs@starkdigital.net or directly apply from website'",
        },
        {
            "name": "Arup Banerjee",
            "email": "hr@specrtagaze.com",
            "role": "HR Leadership",
            "company": "SpectraGaze",
            "domain": "specrtagaze.com",
            "linkedin": "https://www.linkedin.com/in/arup-banerjee-15004567",
            "channel": "corporate",
            "route": "EMAIL",
            "evidence": "LinkedIn messaging thread: 'Please contact hr@specrtagaze.com'",
        },
        {
            "name": "Navnath Aar",
            "email": "navnathaar3327@gmail.com",
            "role": "QA / Software Contact",
            "company": "Software QA Network",
            "domain": "gmail.com",
            "linkedin": "https://www.linkedin.com/in/navnath-aar-4b9638255",
            "channel": "personal",
            "route": "EMAIL",
            "evidence": "LinkedIn message: QA Engineer referral and application thread",
        },
        {
            "name": "Sharang Dhaimade",
            "email": "sharang@seedglobaleducation.com",
            "role": "Recruitment & Partnerships Lead",
            "company": "Seed Global Education",
            "domain": "seedglobaleducation.com",
            "linkedin": None,
            "channel": "corporate",
            "route": "EMAIL",
            "evidence": "LinkedIn outreach thread regarding leadership & technical hiring programs",
        },
    ]

    for rm in recruiter_messages:
        pair = (rm["email"], rm["role"])
        if pair not in seen_pairs:
            seen_pairs.add(pair)
            leads_to_ingest.append({
                "lead_id": f"lead_{uuid.uuid4().hex[:12]}",
                "company_name": rm["company"],
                "company_domain": rm["domain"],
                "role_title": rm["role"],
                "contact_name": rm["name"],
                "contact_email": rm["email"],
                "contact_linkedin_url": rm["linkedin"],
                "contact_type": "inbound_recruiter",
                "source_platform": "linkedin_messages",
                "evidence_snippet": rm["evidence"],
                "special_instructions_json": json.dumps({"source": "messages.csv"}),
                "execution_route": rm["route"],
                "outreach_status": "queued",
                "preferred_channel": rm["channel"],
                "persona": "recruiter",
                "priority_score": 95,
                "personal_email": rm["email"] if rm["channel"] == "personal" else None,
            })

    logger.info(
        "Prepared %d leads for ingestion (DMs: %d, Secs: %d, LI-Only: %d, Personal: %d, Corporate: %d, Messages: %d)",
        len(leads_to_ingest), total_dms_processed, total_secs_processed, linkedin_only_count,
        personal_email_count, corporate_email_count, len(recruiter_messages),
    )

    if not dry_run:
        now_iso = datetime.now(timezone.utc).isoformat()
        cursor = conn.cursor()
        for ld in leads_to_ingest:
            cursor.execute(
                """
                INSERT INTO recruiter_leads (
                    lead_id, company_name, company_domain, role_title,
                    contact_name, contact_email, contact_linkedin_url,
                    contact_type, source_platform, evidence_snippet,
                    special_instructions_json, execution_route, outreach_status,
                    preferred_channel, persona, priority_score, personal_email, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(contact_email, role_title) DO UPDATE SET
                    company_name = COALESCE(excluded.company_name, recruiter_leads.company_name),
                    company_domain = COALESCE(excluded.company_domain, recruiter_leads.company_domain),
                    contact_name = COALESCE(excluded.contact_name, recruiter_leads.contact_name),
                    contact_linkedin_url = COALESCE(excluded.contact_linkedin_url, recruiter_leads.contact_linkedin_url),
                    evidence_snippet = COALESCE(excluded.evidence_snippet, recruiter_leads.evidence_snippet),
                    preferred_channel = COALESCE(excluded.preferred_channel, recruiter_leads.preferred_channel),
                    execution_route = COALESCE(excluded.execution_route, recruiter_leads.execution_route),
                    priority_score = MAX(excluded.priority_score, recruiter_leads.priority_score),
                    personal_email = COALESCE(excluded.personal_email, recruiter_leads.personal_email)
                """,
                (
                    ld["lead_id"],
                    ld["company_name"],
                    ld["company_domain"],
                    ld["role_title"],
                    ld["contact_name"],
                    ld["contact_email"],
                    ld["contact_linkedin_url"],
                    ld["contact_type"],
                    ld["source_platform"],
                    ld["evidence_snippet"],
                    ld["special_instructions_json"],
                    ld["execution_route"],
                    ld["outreach_status"],
                    ld["preferred_channel"],
                    ld["persona"],
                    ld["priority_score"],
                    ld.get("personal_email"),
                    now_iso,
                ),
            )

    return {
        "initial_count": initial_count,
        "total_leads_prepared": len(leads_to_ingest),
        "total_dms_processed": total_dms_processed,
        "total_secs_processed": total_secs_processed,
        "personal_emails": personal_email_count,
        "corporate_emails": corporate_email_count,
        "linkedin_only": linkedin_only_count,
        "recruiter_messages": len(recruiter_messages),
    }


# ==============================================================================
# 3. Jobs & History Ingestion
# ==============================================================================

def ingest_jobs_and_history(
    conn: sqlite3.Connection,
    data_dir: Path = DEFAULT_DATA_DIR,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Ingest curated jobs, saved roles, and submitted past applications into jobs table."""
    logger.info("--- Starting Jobs & History Ingestion ---")

    initial_count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    logger.info("Current jobs count: %d", initial_count)

    jobs_to_upsert: List[Dict[str, Any]] = []
    seen_urls: Set[str] = set()

    # 1. Ingest 58 Curated Roles from Job Hunt Master Jobs Database
    master_jobs_path = data_dir / "Job Hunt" / "data" / "master_jobs_database.csv"
    curated_count = 0
    if master_jobs_path.exists():
        with open(master_jobs_path, "r", encoding="utf-8-sig", errors="replace") as f:
            for r in csv.DictReader(f):
                job_id = r.get("Job ID", "").strip()
                app_url = r.get("Application URL", "").strip()
                title = r.get("Job Title", "").strip()
                company = r.get("Company Name", "").strip()
                source = r.get("Source", "Job Hunt Master").strip()
                location = r.get("Location", "").strip()
                salary = r.get("Compensation", "").strip()
                score_str = r.get("Fit Score", "").strip()
                fit_score = int(score_str) if score_str.isdigit() else 85
                notes = r.get("Notes", "").strip()
                evidence = r.get("Evidence", "").strip()

                if not app_url:
                    continue

                # Disambiguate duplicate URLs
                if app_url in seen_urls:
                    app_url = f"{app_url}#role-{job_id or uuid.uuid4().hex[:6]}"
                seen_urls.add(app_url)

                jobs_to_upsert.append({
                    "url": app_url,
                    "title": title,
                    "company": company,
                    "salary": salary or None,
                    "description": f"{evidence} | {notes}".strip(" | "),
                    "location": location or None,
                    "site": source.lower(),
                    "strategy": "curated_jobhunt_master",
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                    "fit_score": fit_score,
                    "state": "discovered",
                    "apply_status": None,
                    "applied_at": None,
                })
                curated_count += 1
        logger.info("Processed %d curated roles from master_jobs_database.csv", curated_count)

    # 2. Ingest 23 Saved Roles from Saved Jobs.csv
    saved_jobs_path = data_dir / "my linkedin data" / "Jobs" / "Saved Jobs.csv"
    saved_count = 0
    if saved_jobs_path.exists():
        with open(saved_jobs_path, "r", encoding="utf-8-sig", errors="replace") as f:
            for r in csv.DictReader(f):
                app_url = r.get("Job Url", "").strip()
                saved_date = r.get("Saved Date", "").strip()
                title = r.get("Job Title", "").strip() or "Saved Role"
                company = r.get("Company Name", "").strip() or "LinkedIn Employer"

                if not app_url:
                    continue

                if app_url in seen_urls:
                    app_url = f"{app_url}#saved-{uuid.uuid4().hex[:6]}"
                seen_urls.add(app_url)

                jobs_to_upsert.append({
                    "url": app_url,
                    "title": title,
                    "company": company,
                    "salary": None,
                    "description": f"Saved by user on LinkedIn ({saved_date})",
                    "location": None,
                    "site": "linkedin",
                    "strategy": "saved_job",
                    "discovered_at": saved_date or datetime.now(timezone.utc).isoformat(),
                    "fit_score": 80,
                    "state": "discovered",
                    "apply_status": None,
                    "applied_at": None,
                })
                saved_count += 1
        logger.info("Processed %d saved roles from Saved Jobs.csv", saved_count)

    # 3. Ingest 108 Submitted Past Applications from Job Applications.csv
    applications_path = data_dir / "my linkedin data" / "Jobs" / "Job Applications.csv"
    apps_count = 0
    if applications_path.exists():
        with open(applications_path, "r", encoding="utf-8-sig", errors="replace") as f:
            for r in csv.DictReader(f):
                app_url = r.get("Job Url", "").strip()
                app_date = r.get("Application Date", "").strip()
                title = r.get("Job Title", "").strip() or "Applied Role"
                company = r.get("Company Name", "").strip() or "LinkedIn Employer"
                resume = r.get("Resume Name", "").strip()

                if not app_url:
                    continue

                # Note: Keep original application URL; if seen previously in curated, overrides it to applied
                seen_urls.add(app_url)

                jobs_to_upsert.append({
                    "url": app_url,
                    "title": title,
                    "company": company,
                    "salary": None,
                    "description": f"Submitted LinkedIn application with resume: {resume}",
                    "location": None,
                    "site": "linkedin",
                    "strategy": "historical_application",
                    "discovered_at": app_date or datetime.now(timezone.utc).isoformat(),
                    "fit_score": 90,
                    "state": "applied",
                    "apply_status": "submitted",
                    "applied_at": app_date or datetime.now(timezone.utc).isoformat(),
                })
                apps_count += 1
        logger.info("Processed %d historical submitted applications from Job Applications.csv", apps_count)

    if not dry_run:
        cursor = conn.cursor()
        for jb in jobs_to_upsert:
            cursor.execute(
                """
                INSERT INTO jobs (
                    url, title, company, salary, description, location,
                    site, strategy, discovered_at, fit_score, state,
                    apply_status, applied_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    title = COALESCE(excluded.title, jobs.title),
                    company = COALESCE(excluded.company, jobs.company),
                    salary = COALESCE(excluded.salary, jobs.salary),
                    description = COALESCE(excluded.description, jobs.description),
                    location = COALESCE(excluded.location, jobs.location),
                    site = COALESCE(excluded.site, jobs.site),
                    strategy = COALESCE(excluded.strategy, jobs.strategy),
                    discovered_at = COALESCE(excluded.discovered_at, jobs.discovered_at),
                    fit_score = COALESCE(excluded.fit_score, jobs.fit_score),
                    state = CASE WHEN excluded.state = 'applied' THEN 'applied' ELSE jobs.state END,
                    apply_status = CASE WHEN excluded.apply_status = 'submitted' THEN 'submitted' ELSE jobs.apply_status END,
                    applied_at = COALESCE(excluded.applied_at, jobs.applied_at)
                """,
                (
                    jb["url"],
                    jb["title"],
                    jb["company"],
                    jb["salary"],
                    jb["description"],
                    jb["location"],
                    jb["site"],
                    jb["strategy"],
                    jb["discovered_at"],
                    jb["fit_score"],
                    jb["state"],
                    jb["apply_status"],
                    jb["applied_at"],
                ),
            )

    return {
        "initial_count": initial_count,
        "curated_roles": curated_count,
        "saved_roles": saved_count,
        "submitted_applications": apps_count,
        "total_jobs_prepared": len(jobs_to_upsert),
    }


# ==============================================================================
# 4. Screening Q&A Knowledge & FTS5 Synchronization
# ==============================================================================

def ingest_screening_qa_and_sync_fts(
    conn: sqlite3.Connection,
    data_dir: Path = DEFAULT_DATA_DIR,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Parse screening responses and application QA blocks, dual-writing to qa_knowledge and synchronizing qa_fts."""
    logger.info("--- Starting Q&A Knowledge & FTS5 Ingestion ---")

    initial_qa_count = conn.execute("SELECT COUNT(*) FROM qa_knowledge").fetchone()[0]
    initial_fts_count = conn.execute("SELECT COUNT(*) FROM qa_fts").fetchone()[0]
    logger.info("Current QA counts: qa_knowledge=%d, qa_fts=%d", initial_qa_count, initial_fts_count)

    qa_items: List[Tuple[str, str, str]] = []  # (question_text, answer_text, source)
    profile_fallbacks = load_profile_fallbacks(data_dir)

    # 1. 83 screening questions from Job Applicant Saved Screening Question Responses.csv
    saved_qa_path = data_dir / "my linkedin data" / "Job Applicant Saved Screening Question Responses.csv"
    saved_qa_count = 0
    if saved_qa_path.exists():
        with open(saved_qa_path, "r", encoding="utf-8-sig", errors="replace") as f:
            for r in csv.DictReader(f):
                q = r.get("Question", "").strip()
                a = r.get("Answer", "").strip()
                if not a:
                    a = profile_fallbacks.get(q, "")
                if q and a:
                    qa_items.append((q, a, "linkedin_screening_response"))
                    saved_qa_count += 1
        logger.info("Loaded %d questions from Job Applicant Saved Screening Question Responses.csv", saved_qa_count)

    # 2. 237 unique questions from 90 Question And Answers blocks in Job Applications.csv
    apps_path = data_dir / "my linkedin data" / "Jobs" / "Job Applications.csv"
    app_blocks_processed = 0
    app_pairs_extracted = 0
    if apps_path.exists():
        with open(apps_path, "r", encoding="utf-8-sig", errors="replace") as f:
            for r in csv.DictReader(f):
                block = r.get("Question And Answers", "").strip()
                if not block:
                    continue
                app_blocks_processed += 1
                items = block.split(" | ")
                for item in items:
                    item = item.strip()
                    if ":" in item:
                        q, a = item.split(":", 1)
                        q = q.strip()
                        a = a.strip()
                        if q and a:
                            qa_items.append((q, a, "linkedin_application_qa"))
                            app_pairs_extracted += 1

        logger.info(
            "Parsed %d application QA blocks, extracting %d QA pairs",
            app_blocks_processed, app_pairs_extracted
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    unique_inserted = 0

    if not dry_run:
        cursor = conn.cursor()
        for q_text, a_text, source in qa_items:
            key = question_key(q_text)
            q_hash = hashlib.sha256(normalize_question(q_text).encode("utf-8")).hexdigest()
            canonical_q = q_text

            # Upsert into qa_knowledge
            cursor.execute(
                """
                INSERT INTO qa_knowledge (
                    question_text, question_key, canonical_question, question_hash,
                    answer_text, answer_source, source, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(question_key, answer_text) DO UPDATE SET
                    updated_at = excluded.updated_at,
                    use_count = qa_knowledge.use_count + 1
                """,
                (q_text, key, canonical_q, q_hash, a_text, source, source, now_iso, now_iso),
            )

        # Full synchronization: Prune orphaned FTS rows and ensure all qa_knowledge rows are indexed in qa_fts
        cursor.execute("DELETE FROM qa_fts WHERE rowid NOT IN (SELECT id FROM qa_knowledge)")
        cursor.execute(
            """
            INSERT OR REPLACE INTO qa_fts (rowid, question_key, canonical_question, question_text, answer_text)
            SELECT id, question_key, canonical_question, question_text, answer_text FROM qa_knowledge
            """
        )
        final_qa = conn.execute("SELECT COUNT(*) FROM qa_knowledge").fetchone()[0]
        final_fts = conn.execute("SELECT COUNT(*) FROM qa_fts").fetchone()[0]
        logger.info("Synchronized qa_fts with qa_knowledge: %d rows (FTS=%d)", final_qa, final_fts)
        unique_inserted = final_qa

    return {
        "initial_qa_knowledge": initial_qa_count,
        "initial_qa_fts": initial_fts_count,
        "saved_questions": saved_qa_count,
        "app_blocks_processed": app_blocks_processed,
        "app_pairs_extracted": app_pairs_extracted,
        "total_qa_items_processed": len(qa_items),
        "unique_records_synced": unique_inserted,
    }


# ==============================================================================
# 5. Future LinkedIn Connections Ingestion Hook
# ==============================================================================

def ingest_linkedin_connections(
    conn: sqlite3.Connection,
    connections_csv_path: Optional[Path | str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Parse LinkedIn Connections.csv and link 1st-degree referrers to career_watchlist companies."""
    logger.info("--- Checking LinkedIn Connections Hook ---")

    csv_path = Path(connections_csv_path) if connections_csv_path else (DEFAULT_DATA_DIR / "my linkedin data" / "Connections.csv")

    if not csv_path.exists():
        logger.info(
            "Connections.csv not found at '%s'. "
            "To unlock ~5,500 1st-degree referrals, download your Connections archive from "
            "https://www.linkedin.com/mypreferences/d/download-my-data and place it at that path.",
            csv_path,
        )
        return {
            "status": "pending_upload",
            "message": f"Connections.csv not found at {csv_path}",
            "connections_count": 0,
            "matched_companies": 0,
        }

    logger.info("Found Connections.csv at '%s'. Parsing connections...", csv_path)

    # Locate header line in Connections.csv
    lines: List[str] = []
    with open(csv_path, "r", encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            if "Company" in line and ("First Name" in line or "Position" in line):
                lines.append(line)
                lines.extend(f.readlines())
                break

    if not lines:
        logger.warning("Could not identify header in Connections.csv")
        return {"status": "invalid_format", "connections_count": 0, "matched_companies": 0}

    reader = csv.DictReader(lines)
    connections = list(reader)
    matched_companies = 0

    # Build fast in-memory normalized lookup for watchlist companies
    rows = conn.execute("SELECT company_id, company_name, official_domain FROM career_watchlist").fetchall()
    name_map: Dict[str, str] = {}
    for r in rows:
        cid = r[0]
        raw_n = (r[1] or "").strip().lower()
        norm_n = normalize_company_name(r[1] or "").lower()
        if raw_n:
            name_map[raw_n] = cid
        if norm_n:
            name_map[norm_n] = cid

    cursor = conn.cursor()
    for row in connections:
        comp_raw = row.get("Company", "").strip()
        first_name = row.get("First Name", "").strip()
        last_name = row.get("Last Name", "").strip()
        li_url = row.get("URL", "").strip()
        referrer_name = f"{first_name} {last_name}".strip()

        if not comp_raw or not referrer_name:
            continue

        raw_key = comp_raw.lower()
        norm_key = normalize_company_name(comp_raw).lower()
        cid = name_map.get(raw_key) or name_map.get(norm_key)

        if cid:
            matched_companies += 1
            if not dry_run:
                cursor.execute(
                    """
                    UPDATE career_watchlist
                    SET referral_available = 1,
                        referrer_name = COALESCE(career_watchlist.referrer_name, ?),
                        referrer_linkedin = COALESCE(career_watchlist.referrer_linkedin, ?)
                    WHERE company_id = ?
                    """,
                    (referrer_name, li_url or None, cid),
                )

    logger.info("LinkedIn Connections Hook matched %d companies in career_watchlist", matched_companies)
    return {
        "status": "success",
        "connections_count": len(connections),
        "matched_companies": matched_companies,
    }


# ==============================================================================
# CLI Entrypoint & Runner
# ==============================================================================

def run_pipeline(
    db_path: Path | str = DB_PATH,
    data_dir: Path = DEFAULT_DATA_DIR,
    commit: bool = False,
    connections_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """Execute complete ingestion pipeline with explicit transaction management."""
    dry_run = not commit
    mode_str = "LIVE COMMIT" if commit else "DRY RUN (Preview Only)"
    logger.info("=================================================================")
    logger.info("Running ApplyPilot Local Data Ingestion: %s", mode_str)
    logger.info("Target DB: %s", db_path)
    logger.info("Data Dir:  %s", data_dir)
    logger.info("=================================================================")

    # Setup connection
    conn = get_connection(db_path)
    init_db(conn)
    run_migrations(conn)

    results: Dict[str, Any] = {}

    try:
        if commit:
            conn.execute("BEGIN TRANSACTION")

        # 1. Career Watchlist
        results["career_watchlist"] = ingest_career_watchlist(conn, data_dir=data_dir, dry_run=dry_run)

        # 2. Recruiter Leads
        results["recruiter_leads"] = ingest_recruiter_leads(conn, data_dir=data_dir, dry_run=dry_run)

        # 3. Jobs & History
        results["jobs"] = ingest_jobs_and_history(conn, data_dir=data_dir, dry_run=dry_run)

        # 4. Screening QA & FTS5
        results["screening_qa"] = ingest_screening_qa_and_sync_fts(conn, data_dir=data_dir, dry_run=dry_run)

        # 5. Connections Hook
        results["connections_hook"] = ingest_linkedin_connections(conn, connections_csv_path=connections_path, dry_run=dry_run)

        if commit:
            conn.commit()
            logger.info("Successfully committed all changes to %s", db_path)
        else:
            conn.rollback()
            logger.info("Dry run completed cleanly. All database changes rolled back.")

    except Exception as exc:
        conn.rollback()
        logger.error("Pipeline failed with exception: %s", exc, exc_info=True)
        raise exc

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest GTM, Job Hunt, and LinkedIn datasets into ApplyPilot.")
    parser.add_argument("--commit", action="store_true", help="Permanently commit changes to the database.")
    parser.add_argument("--dry-run", action="store_true", help="Preview ingestion without making permanent changes (default).")
    parser.add_argument("--db-path", type=str, default=str(DB_PATH), help="Path to ApplyPilot SQLite database.")
    parser.add_argument("--data-dir", type=str, default=str(DEFAULT_DATA_DIR), help="Path to data-we-can-use directory.")
    parser.add_argument("--connections-path", type=str, default=None, help="Path to LinkedIn Connections.csv.")

    args = parser.parse_args()

    commit = args.commit and not args.dry_run

    results = run_pipeline(
        db_path=Path(args.db_path),
        data_dir=Path(args.data_dir),
        commit=commit,
        connections_path=args.connections_path,
    )

    print("\n" + "=" * 60)
    print("INGESTION SUMMARY REPORT")
    print("=" * 60)
    print(f"Mode: {'PERMANENT COMMIT' if commit else 'DRY RUN'}")
    print(f"Target Database: {args.db_path}\n")

    wl = results["career_watchlist"]
    print("1. CAREER WATCHLIST (career_watchlist)")
    print(f"   • Initial Companies: {wl['initial_count']}")
    print(f"   • Post-Ingestion Total: {wl['total_records']} (+{wl['net_new']} net-new)")
    print(f"   • Tier 1 (VIP): {wl['tier1_vip']}")
    print(f"   • Tier 2: {wl['tier2']}")
    print(f"   • Tier 3: {wl['tier3']}")
    print(f"   • GTM Excluded (Do Not Target): {wl['gtm_excluded']}")
    print(f"   • Consolidated Pre-existing Duplicates: {wl['pruned_duplicates']}\n")

    ld = results["recruiter_leads"]
    print("2. RECRUITER LEADS (recruiter_leads)")
    print(f"   • Initial Leads: {ld['initial_count']}")
    print(f"   • Leads Prepared: {ld['total_leads_prepared']}")
    print(f"   • Decision-Makers Processed: {ld['total_dms_processed']}")
    print(f"   • Secondary Contacts Processed: {ld['total_secs_processed']}")
    print(f"   • LinkedIn-Only Executives: {ld['linkedin_only']}")
    print(f"   • Personal Emails: {ld['personal_emails']}")
    print(f"   • Corporate / Inquiries: {ld['corporate_emails']}")
    print(f"   • Verified Inbound Messages: {ld['recruiter_messages']}\n")

    jb = results["jobs"]
    print("3. JOBS & HISTORICAL APPLICATIONS (jobs)")
    print(f"   • Initial Jobs: {jb['initial_count']}")
    print(f"   • Curated Job Hunt Roles: {jb['curated_roles']}")
    print(f"   • Hand-Saved LinkedIn Roles: {jb['saved_roles']}")
    print(f"   • Submitted Past Applications: {jb['submitted_applications']}")
    print(f"   • Total Active + Historical Jobs: {jb['initial_count'] + jb['total_jobs_prepared']}\n")

    qa = results["screening_qa"]
    print("4. SCREENING Q&A & FULL-TEXT SEARCH (qa_knowledge & qa_fts)")
    print(f"   • Initial QA Knowledge / FTS: {qa['initial_qa_knowledge']} / {qa['initial_qa_fts']}")
    print(f"   • Saved Screening Questions (All Resolved): {qa['saved_questions']}")
    print(f"   • Application QA Blocks: {qa['app_blocks_processed']} (Yielded {qa['app_pairs_extracted']} Q&A pairs)")
    print(f"   • Total Processed Items: {qa['total_qa_items_processed']}")
    print(f"   • Final Synchronized Q&A Records: {qa['unique_records_synced']}\n")

    cn = results["connections_hook"]
    print("5. LINKEDIN CONNECTIONS HOOK")
    print(f"   • Status: {cn['status']}")
    print(f"   • Connections Processed: {cn['connections_count']}")
    print(f"   • Matched Employers: {cn['matched_companies']}\n")
    print("=" * 60)


if __name__ == "__main__":
    main()
