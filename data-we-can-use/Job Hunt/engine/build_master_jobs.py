import csv
import json
import re
import os
from pathlib import Path
import pandas as pd
from engine.db import get_connection
from engine.scoring import score_job

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

def slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s.strip("-")

def read_source_csv(path: str):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [c.lstrip("\ufeff").strip() for c in reader.fieldnames]
        for r in reader:
            rows.append(r)
    return rows

def build_jobs():
    root = Path(__file__).resolve().parent.parent

    # Load source jobs
    expanded_jobs = read_source_csv(str(root / "ai_software_jobs_15_sources_expanded_2026-10-10.csv"))
    ref_jobs = read_source_csv(str(root / "referral_jobs_tracker.csv"))

    # Map referral jobs data by company + job title
    ref_map = {}
    for r in ref_jobs:
        key = (r.get("Company", "").strip().lower(), r.get("Job title", "").strip().lower())
        ref_map[key] = r

    jobs_dict = {}

    for r in expanded_jobs:
        company_name = r.get("Company", "").strip()
        job_title = r.get("Job Title", "").strip()
        if not company_name or not job_title:
            continue

        job_key = (company_name.lower(), job_title.lower())
        ref_match = ref_map.get(job_key, {})

        job_id = f"{slugify(company_name)}-{slugify(job_title)}"
        # Ensure unique id
        counter = 1
        base_id = job_id
        while job_id in jobs_dict:
            job_id = f"{base_id}-{counter}"
            counter += 1

        source = r.get("Source", "").strip()
        location = r.get("Location", "").strip()
        exp = r.get("Experience", "").strip()
        salary = r.get("Advertised Compensation", "").strip()
        skills = r.get("Skills Match", "").strip()
        url = r.get("Listing or Search URL", "").strip()
        evidence = r.get("Evidence Type", "").strip()
        app_status = r.get("Application Status", "").strip()
        research_date = r.get("Research Date", "").strip()

        # Map status to Kanban pipeline stages
        # Stages: 'Discovered', 'Referral Sourced', 'Applied Directly', 'Followed Up', 'Screening / OA', 'Technical Interview', 'Final / Offer'
        kanban_status = "Discovered"
        if app_status.lower() in ["applied", "submitted"]:
            kanban_status = "Applied Directly"
        elif ref_match.get("Referral outreach status", "").lower() in ["contacted", "referred", "messaged"]:
            kanban_status = "Referral Sourced"

        job_obj = {
            "job_id": job_id,
            "company_id": slugify(company_name),
            "company_name": company_name,
            "job_title": job_title,
            "source": source,
            "location": location,
            "experience_req": exp,
            "salary_or_equity": salary,
            "required_skills": skills,
            "application_url": url,
            "evidence_type": evidence,
            "status": kanban_status,
            "posted_date": research_date or "2026-10-10",
            "applied_date": "",
            "follow_up_date": "",
            "notes": f"CV Fit: {r.get('CV Fit Assessment', '')}. India Eligibility: {r.get('India/Pune Eligibility', '')}",
            "raw_metadata": {
                "source_expanded": r,
                "referral_tracker": ref_match
            }
        }

        # Calculate fit score and tier
        score, tier, breakdown = score_job(job_obj)
        job_obj["fit_score"] = score
        job_obj["fit_tier"] = tier
        job_obj["fit_breakdown"] = json.dumps(breakdown)

        jobs_dict[job_id] = job_obj

    # Save to SQLite
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jobs")

    insert_rows = []
    for j in jobs_dict.values():
        insert_rows.append((
            j["job_id"],
            j["company_id"],
            j["company_name"],
            j["job_title"],
            j["source"],
            j["location"],
            j["experience_req"],
            j["salary_or_equity"],
            j["required_skills"],
            j["application_url"],
            j["fit_score"],
            j["fit_tier"],
            j["fit_breakdown"],
            j["evidence_type"],
            j["status"],
            j["notes"],
            j["posted_date"],
            j["applied_date"],
            j["follow_up_date"],
            json.dumps(j["raw_metadata"], ensure_ascii=False)
        ))

    cursor.executemany("""
    INSERT INTO jobs (
        job_id, company_id, company_name, job_title, source, location,
        experience_req, salary_or_equity, required_skills, application_url,
        fit_score, fit_tier, fit_breakdown, evidence_type, status, notes,
        posted_date, applied_date, follow_up_date, raw_metadata
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, insert_rows)

    conn.commit()
    conn.close()

    # Export to CSV & Excel
    export_df = pd.DataFrame([{
        "Job ID": j["job_id"],
        "Company Name": j["company_name"],
        "Job Title": j["job_title"],
        "Source": j["source"],
        "Location": j["location"],
        "Experience": j["experience_req"],
        "Compensation": j["salary_or_equity"],
        "Skills": j["required_skills"],
        "Fit Score": j["fit_score"],
        "Fit Tier": j["fit_tier"],
        "Pipeline Status": j["status"],
        "Application URL": j["application_url"],
        "Evidence": j["evidence_type"],
        "Notes": j["notes"]
    } for j in jobs_dict.values()])

    csv_path = DATA_DIR / "master_jobs_database.csv"
    xlsx_path = DATA_DIR / "master_jobs_database.xlsx"

    export_df.to_csv(csv_path, index=False)
    export_df.to_excel(xlsx_path, index=False)

    print(f"Successfully processed {len(jobs_dict)} verified jobs!")
    print(f"Fit Tier Breakdown: {export_df['Fit Tier'].value_counts().to_dict()}")
    print(f"Saved to:\n - SQLite: job_hunt.db\n - CSV: {csv_path}\n - XLSX: {xlsx_path}")
    return len(jobs_dict)

if __name__ == "__main__":
    build_jobs()
