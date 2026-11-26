import requests
import json
import re
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

def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    clean = re.sub(r"<[^>]+>", " ", raw_html)
    return re.sub(r"\s+", " ", clean).strip()

def fetch_himalayas_jobs():
    url = "https://himalayas.app/jobs/api?limit=50"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    extracted = []
    try:
        res = requests.get(url, headers=headers, timeout=12)
        if res.status_code == 200:
            data = res.json()
            jobs = data.get("jobs", [])
            for j in jobs:
                title = j.get("title", "")
                company = j.get("companyName", "")
                restrictions = j.get("locationRestrictions", [])
                
                # Check for AI / Python / Backend keywords
                full_text = f"{title} {j.get('excerpt', '')} {' '.join(j.get('categories', []))}".lower()
                is_ai_or_backend = any(k in full_text for k in [
                    "ai", "ml", "llm", "agent", "python", "backend", "full stack", 
                    "machine learning", "data engineer", "software engineer", "fastapi"
                ])
                if not is_ai_or_backend:
                    continue

                # Check India eligibility
                is_india_eligible = False
                loc_str = "Worldwide Remote"
                if not restrictions or "Worldwide" in restrictions or "Anywhere" in restrictions:
                    is_india_eligible = True
                    loc_str = "Remote Worldwide"
                elif "India" in restrictions:
                    is_india_eligible = True
                    loc_str = "Remote India"
                elif any("asia" in r.lower() for r in restrictions):
                    is_india_eligible = True
                    loc_str = "Remote (Asia / APAC)"

                if not is_india_eligible:
                    continue

                salary = ""
                min_s = j.get("minSalary")
                max_s = j.get("maxSalary")
                curr = j.get("currency", "$")
                if min_s and max_s:
                    salary = f"{curr}{min_s:,} - {curr}{max_s:,} / {j.get('salaryPeriod', 'year')}"

                posted_dt = str(j.get("pubDate") or "")
                if len(posted_dt) > 10 and not posted_dt.isdigit():
                    posted_dt = posted_dt[:10]

                sen = j.get("seniority")
                sen_str = ", ".join(sen) if isinstance(sen, list) else str(sen or "Mid / Associate")

                job_obj = {
                    "job_id": f"himalayas-{slugify(company)}-{slugify(title)}",
                    "company_id": slugify(company),
                    "company_name": company,
                    "job_title": title,
                    "source": "Himalayas",
                    "location": loc_str,
                    "experience_req": sen_str,
                    "salary_or_equity": salary,
                    "required_skills": ", ".join(j.get("categories", [])) or "Python, AI, APIs",
                    "application_url": j.get("applicationLink") or f"https://himalayas.app/companies/{j.get('companySlug')}/jobs",
                    "evidence_type": "Live Himalayas Feed",
                    "status": "Discovered",
                    "posted_date": posted_dt,
                    "applied_date": "",
                    "follow_up_date": "",
                    "notes": f"Location restrictions: {', '.join(restrictions) if restrictions else 'Worldwide'}",
                    "raw_metadata": j
                }
                extracted.append(job_obj)
    except Exception as e:
        print(f"Himalayas extraction notice: {e}")
    return extracted

def fetch_remotive_jobs():
    url = "https://remotive.com/api/remote-jobs?category=software-dev&limit=40"
    headers = {"User-Agent": "Mozilla/5.0"}
    extracted = []
    try:
        res = requests.get(url, headers=headers, timeout=12)
        if res.status_code == 200:
            data = res.json()
            jobs = data.get("jobs", [])
            for j in jobs:
                title = j.get("title", "")
                company = j.get("company_name", "")
                loc = j.get("candidate_required_location", "")

                full_text = f"{title} {' '.join(j.get('tags', []))} {clean_html(j.get('description', ''))[:500]}".lower()
                is_ai_or_backend = any(k in full_text for k in [
                    "ai", "ml", "llm", "agent", "python", "backend", "full stack", 
                    "fastapi", "react", "django", "engineer"
                ])
                if not is_ai_or_backend:
                    continue

                # Filter location
                loc_lower = loc.lower()
                if any(bad in loc_lower for bad in ["us only", "usa only", "uk only", "canada only", "eu only", "europe only", "latam only"]):
                    continue

                job_obj = {
                    "job_id": f"remotive-{slugify(company)}-{slugify(title)}",
                    "company_id": slugify(company),
                    "company_name": company,
                    "job_title": title,
                    "source": "Remotive",
                    "location": f"Remote ({loc})" if loc else "Remote Worldwide",
                    "experience_req": "All levels / 0-3 yrs",
                    "salary_or_equity": j.get("salary") or "Competitive",
                    "required_skills": ", ".join(j.get("tags", [])) or "Python, Backend, Cloud",
                    "application_url": j.get("url"),
                    "evidence_type": "Live Remotive Feed",
                    "status": "Discovered",
                    "posted_date": (j.get("publication_date") or "")[:10],
                    "applied_date": "",
                    "follow_up_date": "",
                    "notes": f"Candidate Location: {loc}",
                    "raw_metadata": j
                }
                extracted.append(job_obj)
    except Exception as e:
        print(f"Remotive extraction notice: {e}")
    return extracted

def run_live_ingestion():
    print("Starting Live Active Job Ingestion Engine...")
    himalayas_jobs = fetch_himalayas_jobs()
    remotive_jobs = fetch_remotive_jobs()
    all_new_jobs = himalayas_jobs + remotive_jobs
    print(f"Extracted {len(all_new_jobs)} candidate live postings (Himalayas: {len(himalayas_jobs)}, Remotive: {len(remotive_jobs)})")

    conn = get_connection()
    cursor = conn.cursor()

    # Get existing job IDs
    cursor.execute("SELECT job_id FROM jobs")
    existing_ids = {row["job_id"] for row in cursor.fetchall()}

    added_count = 0
    for j in all_new_jobs:
        if j["job_id"] in existing_ids:
            continue

        score, tier, breakdown = score_job(j)
        j["fit_score"] = score
        j["fit_tier"] = tier
        j["fit_breakdown"] = json.dumps(breakdown)

        cursor.execute("""
        INSERT INTO jobs (
            job_id, company_id, company_name, job_title, source, location,
            experience_req, salary_or_equity, required_skills, application_url,
            fit_score, fit_tier, fit_breakdown, evidence_type, status, notes,
            posted_date, applied_date, follow_up_date, raw_metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            j["job_id"], j["company_id"], j["company_name"], j["job_title"],
            j["source"], j["location"], j["experience_req"], j["salary_or_equity"],
            j["required_skills"], j["application_url"], j["fit_score"], j["fit_tier"],
            j["fit_breakdown"], j["evidence_type"], j["status"], j["notes"],
            j["posted_date"], j["applied_date"], j["follow_up_date"],
            json.dumps(j["raw_metadata"], ensure_ascii=False)
        ))
        existing_ids.add(j["job_id"])
        added_count += 1

    conn.commit()

    # Re-export master jobs CSV and XLSX
    cursor.execute("""
    SELECT job_id, company_name, job_title, source, location, experience_req,
           salary_or_equity, required_skills, fit_score, fit_tier, status,
           application_url, evidence_type, notes
    FROM jobs ORDER BY fit_score DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    df = pd.DataFrame(rows)
    df.rename(columns={
        "job_id": "Job ID",
        "company_name": "Company Name",
        "job_title": "Job Title",
        "source": "Source",
        "location": "Location",
        "experience_req": "Experience",
        "salary_or_equity": "Compensation",
        "required_skills": "Skills",
        "fit_score": "Fit Score",
        "fit_tier": "Fit Tier",
        "status": "Pipeline Status",
        "application_url": "Application URL",
        "evidence_type": "Evidence",
        "notes": "Notes"
    }, inplace=True)

    csv_path = DATA_DIR / "master_jobs_database.csv"
    xlsx_path = DATA_DIR / "master_jobs_database.xlsx"
    df.to_csv(csv_path, index=False)
    df.to_excel(xlsx_path, index=False)

    print(f"Added {added_count} new active jobs to master database!")
    print(f"Total Active Jobs Now: {len(df)}")
    print(f"Tier Breakdown:\n{df['Fit Tier'].value_counts().to_dict()}")
    return added_count, len(df)

if __name__ == "__main__":
    run_live_ingestion()
