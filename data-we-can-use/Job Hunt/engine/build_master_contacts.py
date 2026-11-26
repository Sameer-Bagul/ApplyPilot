import csv
import json
import os
from pathlib import Path
import pandas as pd
from engine.db import get_connection
from engine.pitch_generator import get_contact_search_urls

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

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

def build_contacts():
    root = Path(__file__).resolve().parent.parent
    verified_people = read_source_csv(str(root / "referral_verified_people.csv"))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contacts")

    contacts_list = []

    # 1. Add verified public contacts
    for p in verified_people:
        company = p.get("Company", "").strip()
        person = p.get("Person", "").strip()
        role = p.get("Verified role", "").strip()
        email = p.get("Published business email", "").strip()
        link = p.get("Public source / contact link", "").strip()
        note = f"Position: {p.get('Relevant position', '')}. Evidence: {p.get('Evidence / limitations', '')}"
        
        cid = f"{company.lower()}-{person.lower()}".replace(" ", "-")

        contacts_list.append({
            "contact_id": cid,
            "company_id": company.lower().replace(" ", "-"),
            "company_name": company,
            "person_name": person,
            "role": role,
            "email": email,
            "linkedin_or_source_url": link,
            "contact_type": "Founder" if "founder" in role.lower() or "ceo" in role.lower() else "Engineering Leader",
            "verification_status": "Verified Public",
            "notes": note
        })

    # 2. Add contact search strategies for top P1 companies from the database
    cursor.execute("SELECT company_id, company_name, category, website FROM companies WHERE fit_tier = 'P1' LIMIT 100")
    p1_companies = cursor.fetchall()

    for comp in p1_companies:
        c_id = comp["company_id"]
        c_name = comp["company_name"]
        urls = get_contact_search_urls(c_name)

        # Skip if already has verified contact
        if any(c["company_id"] == c_id for c in contacts_list):
            continue

        contacts_list.append({
            "contact_id": f"{c_id}-founder-lead",
            "company_id": c_id,
            "company_name": c_name,
            "person_name": f"{c_name} Founders & EMs",
            "role": "Founder / Engineering Manager",
            "email": "",
            "linkedin_or_source_url": urls["founders"],
            "contact_type": "Founder",
            "verification_status": "Target Search Query",
            "notes": f"Direct filtered LinkedIn search for {c_name} leadership & engineers"
        })

    # Insert into database
    insert_rows = []
    for c in contacts_list:
        insert_rows.append((
            c["contact_id"],
            c["company_id"],
            c["company_name"],
            c["person_name"],
            c["role"],
            c["email"],
            c["linkedin_or_source_url"],
            c["contact_type"],
            c["verification_status"],
            c["notes"]
        ))

    cursor.executemany("""
    INSERT INTO contacts (
        contact_id, company_id, company_name, person_name, role,
        email, linkedin_or_source_url, contact_type, verification_status, notes
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, insert_rows)

    conn.commit()
    conn.close()

    # Export to CSV & Excel
    export_df = pd.DataFrame(contacts_list)
    csv_path = DATA_DIR / "master_contacts_database.csv"
    xlsx_path = DATA_DIR / "master_contacts_database.xlsx"
    export_df.to_csv(csv_path, index=False)
    export_df.to_excel(xlsx_path, index=False)

    print(f"Successfully processed {len(contacts_list)} contacts & outreach targets!")
    print(f"Saved to:\n - SQLite: job_hunt.db\n - CSV: {csv_path}\n - XLSX: {xlsx_path}")
    return len(contacts_list)

if __name__ == "__main__":
    build_contacts()
