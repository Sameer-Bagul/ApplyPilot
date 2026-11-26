import csv
import json
import re
import os
from pathlib import Path
import pandas as pd
from engine.db import get_connection, init_db

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Known direct career URLs and domains for prominent AI / Tech companies
ENRICHED_PROFILES = {
    "langdock": {"website": "https://www.langdock.com", "careers_url": "https://www.langdock.com/careers", "category": "AI Agents & LLM Platform"},
    "cognition ai": {"website": "https://cognition.ai", "careers_url": "https://jobs.ashbyhq.com/cognition", "category": "AI Coding & Agents (Devin)"},
    "sweep ai": {"website": "https://sweep.dev", "careers_url": "https://www.ycombinator.com/companies/sweep/jobs", "category": "AI DevTools"},
    "codeant ai": {"website": "https://www.codeant.ai", "careers_url": "https://www.codeant.ai/careers", "category": "AI Code Review & Security"},
    "stack ai": {"website": "https://www.stack-ai.com", "careers_url": "https://jobs.ashbyhq.com/stack-ai", "category": "Enterprise AI Workflow & Agents"},
    "langflow": {"website": "https://www.langflow.org", "careers_url": "https://datastax.com/careers", "category": "Visual AI Agent Builder"},
    "agentops": {"website": "https://www.agentops.ai", "careers_url": "https://www.agentops.ai/careers", "category": "Agent Observability & Evals"},
    "maxim ai": {"website": "https://www.getmaxim.ai", "careers_url": "https://www.getmaxim.ai/careers", "category": "GenAI Evaluation Platform"},
    "neptune.ai": {"website": "https://neptune.ai", "careers_url": "https://neptune.ai/careers", "category": "MLOps & Experiment Tracking"},
    "evidently ai": {"website": "https://www.evidentlyai.com", "careers_url": "https://www.evidentlyai.com/careers", "category": "AI Observability & Monitoring"},
    "groq": {"website": "https://groq.com", "careers_url": "https://groq.com/careers", "category": "LPU AI Inference Hardware & Cloud"},
    "coreweave": {"website": "https://www.coreweave.com", "careers_url": "https://www.coreweave.com/careers", "category": "Specialized AI Cloud Infrastructure"},
    "lambda labs": {"website": "https://lambdalabs.com", "careers_url": "https://lambdalabs.com/careers", "category": "GPU Cloud & AI Compute"},
    "materialize": {"website": "https://materialize.com", "careers_url": "https://materialize.com/careers", "category": "Streaming Database Engine"},
    "mindtickle": {"website": "https://www.mindtickle.com", "careers_url": "https://www.mindtickle.com/careers", "category": "Sales Readiness AI & SaaS"},
    "druva": {"website": "https://www.druva.com", "careers_url": "https://www.druva.com/about/careers", "category": "Cloud Data Protection & AI"},
    "e42": {"website": "https://e42.ai", "careers_url": "https://e42.ai/careers", "category": "Autonomous AI Co-workers (Pune)"},
    "anthropic": {"website": "https://www.anthropic.com", "careers_url": "https://www.anthropic.com/careers", "category": "Frontier AI & LLM Research"},
    "cohere": {"website": "https://cohere.com", "careers_url": "https://cohere.com/careers", "category": "Enterprise LLMs & RAG"},
    "scale ai": {"website": "https://scale.com", "careers_url": "https://scale.com/careers", "category": "AI Data & Model Evaluation"},
    "mistral ai": {"website": "https://mistral.ai", "careers_url": "https://mistral.ai/careers", "category": "Open Weight Frontier AI Models"},
    "pinecone": {"website": "https://www.pinecone.io", "careers_url": "https://www.pinecone.io/careers", "category": "Vector Database for RAG"},
    "weaviate": {"website": "https://weaviate.io", "careers_url": "https://weaviate.io/careers", "category": "AI Vector Database & Search"},
    "qdrant": {"website": "https://qdrant.tech", "careers_url": "https://qdrant.tech/careers", "category": "High-Performance Vector Search"},
    "anysphere": {"website": "https://www.cursor.com", "careers_url": "https://www.cursor.com/careers", "category": "Cursor AI Code Editor"},
    "perplexity": {"website": "https://www.perplexity.ai", "careers_url": "https://www.perplexity.ai/careers", "category": "Conversational AI Search Engine"},
    "together ai": {"website": "https://www.together.ai", "careers_url": "https://www.together.ai/careers", "category": "Fast AI Acceleration Cloud"},
    "runpod": {"website": "https://www.runpod.io", "careers_url": "https://www.runpod.io/careers", "category": "Serverless GPU Cloud"},
    "baseten": {"website": "https://www.baseten.co", "careers_url": "https://www.baseten.co/careers", "category": "Serverless LLM Deployment"},
    "activepieces": {"website": "https://www.activepieces.com", "careers_url": "https://www.activepieces.com/careers", "category": "Open Source AI Automation"},
    "ressl ai": {"website": "https://ressl.ai", "careers_url": "https://www.ycombinator.com/companies/ressl-ai/jobs", "category": "AI Agents / Evaluation (YC W26)"},
    "hemut": {"website": "https://hemut.com", "careers_url": "https://www.ycombinator.com/companies/hemut/jobs", "category": "AI Code & Security (YC)"},
    "vela": {"website": "https://tryvela.ai", "careers_url": "https://tryvela.ai", "category": "GenAI Workflow Automation"}
}

def clean_company_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    name = re.sub(r"\s+", " ", name).strip()
    return name

def slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s.strip("-")

def extract_priority(val: Any) -> str:
    if not val or not isinstance(val, str):
        return ""
    v = val.strip().upper()
    if v.startswith("P1") or v.startswith("A") or "HIGH" in v or "STRONGEST" in v:
        return "P1"
    if v.startswith("P2") or v.startswith("B") or "MODERATE" in v or "SOLID" in v:
        return "P2"
    if v.startswith("P3") or v.startswith("C") or "LOW" in v or "GENERAL" in v:
        return "P3"
    return ""

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

def build_companies():
    root = Path(__file__).resolve().parent.parent
    init_db()

    # Load all files
    pune_deep = read_source_csv(str(root / "pune_only_it_companies_deep_research.csv"))
    pune_prospects = read_source_csv(str(root / "pune_remote_ai_company_prospects.csv"))
    ref_master = read_source_csv(str(root / "referral_company_master.csv"))
    worldwide = read_source_csv(str(root / "worldwide_remote_ai_software_companies.csv"))
    yc_list = read_source_csv(str(root / "yc_startups_ai_engineer_target_list.csv"))
    verified_people = read_source_csv(str(root / "referral_verified_people.csv"))

    # Verified people lookup
    people_map = {}
    for p in verified_people:
        c_key = p.get("Company", "").strip().lower()
        if c_key:
            people_map[c_key] = {
                "name": p.get("Person", "").strip(),
                "role": p.get("Verified role", "").strip(),
                "email": p.get("Published business email", "").strip(),
                "source_url": p.get("Public source / contact link", "").strip()
            }

    # Master aggregation dict
    companies_dict = {}

    def get_or_create(company_raw: str):
        name = clean_company_name(company_raw)
        if not name:
            return None
        key = name.lower()
        if key not in companies_dict:
            companies_dict[key] = {
                "company_id": slugify(name),
                "company_name": name,
                "fit_tier": "P3",
                "category": "",
                "location_type": "",
                "pune_cluster": "",
                "pune_office_verified": "Unverified",
                "india_eligible_remote": "Needs Check",
                "website": "",
                "careers_url": "",
                "linkedin_url": "",
                "target_roles": "",
                "notes": "",
                "verified_contact_name": "",
                "verified_contact_role": "",
                "verified_contact_email": "",
                "verified_contact_url": "",
                "source_datasets": set(),
                "raw_metadata": {}
            }
        return companies_dict[key]

    # 1. Process pune_only_it_companies_deep_research.csv
    for r in pune_deep:
        c = get_or_create(r.get("Company", ""))
        if not c: continue
        c["source_datasets"].add("pune_only_it_companies_deep_research.csv")
        c["raw_metadata"].setdefault("pune_only_it_companies_deep_research", []).append(r)

        p = extract_priority(r.get("Resume fit", ""))
        if p == "P1" or (p == "P2" and c["fit_tier"] == "P3"):
            c["fit_tier"] = p

        cluster = r.get("Pune IT cluster(s)", "").strip()
        if cluster and not c["pune_cluster"]:
            c["pune_cluster"] = cluster
        c["location_type"] = "Pune Local"

        conf = r.get("Pune office confidence", "").strip()
        if conf:
            c["pune_office_verified"] = conf

        web = r.get("Official website (known)", "").strip()
        if web and web.startswith("http") and not c["website"]:
            c["website"] = web

        car = r.get("Career page (known, not live-verified)", "").strip()
        if car and car.startswith("http") and not c["careers_url"]:
            c["careers_url"] = car

        best_roles = r.get("Best roles to search", "").strip()
        if best_roles and not c["target_roles"]:
            c["target_roles"] = best_roles

    # 2. Process pune_remote_ai_company_prospects.csv (Contains all 692 dropped prospects)
    for r in pune_prospects:
        c = get_or_create(r.get("Company", ""))
        if not c: continue
        c["source_datasets"].add("pune_remote_ai_company_prospects.csv")
        c["raw_metadata"].setdefault("pune_remote_ai_company_prospects", []).append(r)

        p = extract_priority(r.get("CV-match priority (heuristic)", ""))
        if p == "P1" or (p == "P2" and c["fit_tier"] == "P3"):
            c["fit_tier"] = p

        geo = r.get("Target geography", "").strip()
        if geo and not c["location_type"]:
            c["location_type"] = geo

        roles = r.get("Relevant positions", "").strip()
        if roles and not c["target_roles"]:
            c["target_roles"] = roles

        verified_car = r.get("Verified official careers URL", "").strip()
        if verified_car and verified_car.startswith("http") and not c["careers_url"]:
            c["careers_url"] = verified_car

        rem_elig = r.get("Remote eligibility", "").strip()
        if rem_elig and c["india_eligible_remote"] == "Needs Check":
            c["india_eligible_remote"] = rem_elig

    # 3. Process referral_company_master.csv
    for r in ref_master:
        c = get_or_create(r.get("Company", ""))
        if not c: continue
        c["source_datasets"].add("referral_company_master.csv")
        c["raw_metadata"].setdefault("referral_company_master", []).append(r)

        p = extract_priority(r.get("Priority", ""))
        if p == "P1" or (p == "P2" and c["fit_tier"] == "P3"):
            c["fit_tier"] = p

        loc = r.get("Location or Pune cluster", "").strip()
        if loc and not c["pune_cluster"] and ("Baner" in loc or "Hinjawadi" in loc or "Kharadi" in loc or "Magarpatta" in loc or "Pune" in loc):
            c["pune_cluster"] = loc

        target_role = r.get("Target role / observed role", "").strip()
        if target_role:
            c["target_roles"] = target_role

        car = r.get("Official careers (known / not rechecked)", "").strip()
        if car and car.startswith("http") and not c["careers_url"]:
            c["careers_url"] = car

        job_url = r.get("Job listing URL (if supplied)", "").strip()
        if job_url and job_url.startswith("http") and not c["careers_url"]:
            c["careers_url"] = job_url

        # Check contact details inside referral_company_master
        v_person = r.get("Verified person name", "").strip()
        if v_person and not c["verified_contact_name"]:
            c["verified_contact_name"] = v_person
            c["verified_contact_role"] = r.get("Verified public role", "").strip()
            c["verified_contact_email"] = r.get("Published business email", "").strip()
            c["verified_contact_url"] = r.get("Verified public evidence URL", "").strip()

        india_elig = r.get("India eligibility (unverified unless explicit)", "").strip()
        if india_elig:
            c["india_eligible_remote"] = india_elig

    # 4. Process worldwide_remote_ai_software_companies.csv
    for r in worldwide:
        c = get_or_create(r.get("Company", ""))
        if not c: continue
        c["source_datasets"].add("worldwide_remote_ai_software_companies.csv")
        c["raw_metadata"].setdefault("worldwide_remote_ai_software_companies", []).append(r)

        p = extract_priority(r.get("CV match tier", ""))
        if p == "P1" or (p == "P2" and c["fit_tier"] == "P3"):
            c["fit_tier"] = p

        seg = r.get("Segment", "").strip()
        if seg and not c["category"]:
            c["category"] = seg

        if not c["location_type"]:
            c["location_type"] = "Worldwide Remote"

        india_hiring = r.get("India hiring eligibility", "").strip()
        if india_hiring and ("Explicitly" in india_hiring or "Confirmed" in india_hiring):
            c["india_eligible_remote"] = "Confirmed"

        sug_titles = r.get("Suggested job titles", "").strip()
        if sug_titles and not c["target_roles"]:
            c["target_roles"] = sug_titles

    # 5. Process yc_startups_ai_engineer_target_list.csv
    for r in yc_list:
        c = get_or_create(r.get("Company", ""))
        if not c: continue
        c["source_datasets"].add("yc_startups_ai_engineer_target_list.csv")
        c["raw_metadata"].setdefault("yc_startups_ai_engineer_target_list", []).append(r)

        c["fit_tier"] = "P1"  # YC target list is high priority Tier A
        cat = r.get("Category", "").strip()
        batch = r.get("YC Batch", "").strip()
        if cat:
            c["category"] = f"YC {batch} - {cat}" if batch else cat

        loc = r.get("Listed Location", "").strip()
        if loc:
            c["location_type"] = loc
            if "pune" in loc.lower():
                c["pune_cluster"] = loc

        ind = r.get("India Eligibility", "").strip()
        if ind:
            c["india_eligible_remote"] = ind

        obs_role = r.get("Observed Job / Search Role", "").strip()
        if obs_role:
            c["target_roles"] = obs_role

        fit_why = r.get("Why Resume Fits", "").strip()
        if fit_why:
            c["notes"] = f"Why resume fits: {fit_why}"

    # 6. Attach verified people from referral_verified_people.csv
    for key, c in companies_dict.items():
        if key in people_map and not c["verified_contact_name"]:
            p = people_map[key]
            c["verified_contact_name"] = p["name"]
            c["verified_contact_role"] = p["role"]
            c["verified_contact_email"] = p["email"]
            c["verified_contact_url"] = p["source_url"]

    # 7. Apply Enriched Profiles (Official Domains, Careers URLs, and Categories)
    for key, c in companies_dict.items():
        if key in ENRICHED_PROFILES:
            enr = ENRICHED_PROFILES[key]
            if enr.get("website"):
                c["website"] = enr["website"]
            if enr.get("careers_url"):
                c["careers_url"] = enr["careers_url"]
            if enr.get("category") and (not c["category"] or len(c["category"]) < 10):
                c["category"] = enr["category"]

        # Default category if empty
        if not c["category"]:
            if c["fit_tier"] == "P1":
                c["category"] = "AI / GenAI / Applied Agents"
            elif c["fit_tier"] == "P2":
                c["category"] = "Software & Cloud Engineering"
            else:
                c["category"] = "IT Services & Broad Tech"

        # Default location type if empty
        if not c["location_type"]:
            if c["pune_cluster"]:
                c["location_type"] = "Pune Local"
            else:
                c["location_type"] = "Remote (India / Global)"

    # Write to SQLite
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM companies")

    insert_rows = []
    for key, c in companies_dict.items():
        insert_rows.append((
            c["company_id"],
            c["company_name"],
            c["fit_tier"],
            c["category"],
            c["location_type"],
            c["pune_cluster"],
            c["pune_office_verified"],
            c["india_eligible_remote"],
            c["website"],
            c["careers_url"],
            c["linkedin_url"],
            c["target_roles"],
            c["notes"],
            c["verified_contact_name"],
            c["verified_contact_role"],
            c["verified_contact_email"],
            c["verified_contact_url"],
            ", ".join(sorted(c["source_datasets"])),
            json.dumps(c["raw_metadata"], ensure_ascii=False)
        ))

    cursor.executemany("""
    INSERT INTO companies (
        company_id, company_name, fit_tier, category, location_type,
        pune_cluster, pune_office_verified, india_eligible_remote, website,
        careers_url, linkedin_url, target_roles, notes,
        verified_contact_name, verified_contact_role, verified_contact_email,
        verified_contact_url, source_datasets, raw_metadata
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, insert_rows)

    conn.commit()
    conn.close()

    # Export to Master CSV & Excel
    export_df = pd.DataFrame([{
        "Company ID": c["company_id"],
        "Company Name": c["company_name"],
        "Fit Tier": c["fit_tier"],
        "Category": c["category"],
        "Location Type": c["location_type"],
        "Pune Cluster": c["pune_cluster"],
        "Pune Office Confidence": c["pune_office_verified"],
        "India Remote Eligibility": c["india_eligible_remote"],
        "Website": c["website"],
        "Careers URL": c["careers_url"],
        "LinkedIn URL": c["linkedin_url"],
        "Target Roles": c["target_roles"],
        "Verified Contact Name": c["verified_contact_name"],
        "Verified Contact Role": c["verified_contact_role"],
        "Verified Contact Email": c["verified_contact_email"],
        "Verified Contact Link": c["verified_contact_url"],
        "Source Datasets": ", ".join(sorted(c["source_datasets"])),
        "Notes": c["notes"]
    } for c in companies_dict.values()])

    csv_path = DATA_DIR / "master_companies_database.csv"
    xlsx_path = DATA_DIR / "master_companies_database.xlsx"

    export_df.to_csv(csv_path, index=False)
    export_df.to_excel(xlsx_path, index=False)

    print(f"Successfully processed {len(companies_dict)} companies!")
    print(f"Tier Breakdown: {export_df['Fit Tier'].value_counts().to_dict()}")
    print(f"Saved to:\n - SQLite: job_hunt.db\n - CSV: {csv_path}\n - XLSX: {xlsx_path}")
    return len(companies_dict)

if __name__ == "__main__":
    build_companies()
