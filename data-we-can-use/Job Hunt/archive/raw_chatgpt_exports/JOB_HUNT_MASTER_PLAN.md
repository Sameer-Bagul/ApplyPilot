# 🚀 Master Job Hunt Engine & Dataset Plan
**Target Candidate:** Sameer Bagul  
**Target Roles:** Applied AI Engineer · GenAI / Agentic AI Engineer · RAG Engineer · Python Backend Engineer · Full-Stack AI Engineer  
**Core Stack:** Python, LangGraph, RAG Systems, Multi-Model Orchestration, Playwright, React, Node.js, Docker, AWS  
**Locations:** Pune (On-site / Hybrid) & Remote (India-Eligible / Global Remote)  
**Date Created:** October 12, 2026  
**Status:** Active Implementation Roadmap  

---

## 1. Executive Summary & Repo Diagnostic

### 1.1 The Current Reality: Directory vs. Active Jobs
A forensic audit of the data exported from ChatGPT reveals a critical distinction:
- **Companies / Leads:** **2,056 unique company prospects** exist across the repository.
- **Actual Active Job Leads:** **Only 41 job leads** (across 38 companies) are currently captured.
- **Verified Contacts:** Only **4 individuals across 3 companies** (Hemut, Vela, Mindtickle) have verified public contact details. The remaining 1,361+ rows contain automated LinkedIn keyword search strings (`https://www.linkedin.com/search/results/people/?keywords=...`), not actual people.
- **Verification Gaps:** 
  - 100% (952/952) of the worldwide remote dataset has *unverified* India-hiring eligibility.
  - 72% (251/349) of the Pune companies have *unverified* physical office presence.

### 1.2 Duplicate Data Audit (Files & Rows)
1. **Identical Byte-for-Byte Duplicate Files (MD5 Matches):**
   - `pune_only_it_companies_deep_research (1).csv` and `(2).csv` are exact duplicates of `pune_only_it_companies_deep_research.csv` (349 rows each).
   - `pune_remote_ai_company_prospects (1).csv` is an exact duplicate of `pune_remote_ai_company_prospects.csv` (1,493 rows).
   - *Waste:* Over 1.3 MB of redundant disk space and confusing multi-file copies.
2. **Redundant Dataset Subsets:**
   - `ai_software_jobs_15_resources_2026-10-10.csv` (31 jobs) is an exact subset of `ai_software_jobs_15_sources_expanded_2026-10-10.csv` (41 jobs).
   - `referral_jobs_tracker.csv` contains the exact same 41 jobs, merely reshuffled with referral columns.
3. **Cross-File Company Overlaps & Dropped Data:**
   - **779 companies** appear in 3 different CSV files.
   - **528 companies** appear in 2 different CSV files.
   - **21 companies** appear in 4 different CSV files.
   - **CRITICAL DATA LOSS:** `referral_company_master.csv` (1,364 rows) was created as a master file, but **dropped 692 companies** from `pune_remote_ai_company_prospects.csv`, including **85 tier-P1 high-priority AI/SaaS prospects** (e.g., Langdock, Groq, CoreWeave, Lambda Labs, Materialize).

---

## 2. Statistical Baseline of Current Data

| Metric | Count / Percentage | Notes & Status |
| :--- | :--- | :--- |
| **Total Files in Workspace** | 19 files | 12 CSVs, 5 XLSX, 1 JSON, 1 MD |
| **Byte-Identical Duplicate Files** | 3 files | `(1).csv` and `(2).csv` variants |
| **Total Distinct Companies Across All Datasets** | **2,056 companies** | Deduplicated case-insensitively |
| **Companies in `referral_company_master.csv`** | 1,364 companies | Missing 692 companies from prospects |
| **High Priority Fit (P1 - AI / Agentic / Product)** | **345 companies (16.8%)** | Top targets for Sameer's skill profile |
| **Medium Priority Fit (P2 - Software / Engineering)** | **1,363 companies (66.3%)** | Good for backend/full-stack applications |
| **Broad / General Fit (P3 - Services / Broad SaaS)** | **348 companies (16.9%)** | Fallback targets |
| **Verified Active Job Listings** | **41 listings** | Only 20 direct links, 6 company boards |
| **Verified Direct People Contacts** | **4 people (3 companies)** | Loki Cheema, Gobhanu & Saatvik Korisepati, Jagjot Julka |
| **Companies with Direct Career URLs** | 83 in referral master | Many rely on Google search links |

---

## 3. The 6-Phase Architecture for "The Most Amazing Jobs Dataset"

To transform these raw prospect lists into an actionable application engine, we will execute a 6-phase plan:

```
[Phase 1: Cleanup & Deduplication]
             │
             ▼
[Phase 2: Master Company Knowledge Base (2,056 Clean Companies)]
             │
             ▼
[Phase 3: Active Job Ingestion Engine (Live Openings Across 15+ Sources)]
             │
             ▼
[Phase 4: Candidate-Centric Matching & Scoring (AI / Pune / Remote Fit)]
             │
             ▼
[Phase 5: Referral & Contact Intelligence (Founders, EMs, Recruiters)]
             │
             ▼
[Phase 6: Application Pipeline & Daily Execution Tracker (Kanban / CRM)]
```

---

### Phase 1: Repository Cleanup & Deduplication
**Objective:** Eliminate file chaos, archive raw outputs, and establish single sources of truth.

- [ ] **Step 1.1: File Archival & Organization**
  - Create `archive/raw_chatgpt_exports/` to store raw duplicate downloads (`(1).csv`, `(2).csv`, intermediate 31-row jobs).
  - Retain `ChatGPT-New chat-20261010-1853.md` and `.json` as canonical prompt documentation.
- [ ] **Step 1.2: Resolve Dual Formats (CSV vs. XLSX)**
  - Establish CSV/Parquet as the primary computational data layer, with automated export to formatted Excel workbooks for visual tracking.
- [ ] **Step 1.3: Recover the 692 Dropped Companies**
  - Extract the 692 omitted prospects from `pune_remote_ai_company_prospects.csv`, re-score their priority (especially the 85 P1 targets), and merge them into the master company directory.

---

### Phase 2: Master Company Knowledge Base (2,056 Companies)
**Objective:** Merge all company data into one unified, structured, enriched database.

- [ ] **Step 2.1: Schema Normalization**
  - Schema definition:
    - `company_id`: Canonical slug (`e42`, `langchain`, `druva`)
    - `company_name`: Clean official display name
    - `category`: AI Agents / DevTools / FinTech / Healthcare AI / Cloud Infrastructure
    - `fit_tier`: P1 (Direct AI/Agent match), P2 (Backend/Full-Stack), P3 (General)
    - `location_type`: Pune Local / India Remote / Worldwide Remote / Hybrid
    - `pune_cluster`: Hinjawadi, Kharadi, Magarpatta, Baner, Yerawada, or Remote
    - `pune_office_verified`: Boolean (Verified physical presence vs unverified lead)
    - `india_eligible_remote`: Boolean / Needs Check
    - `careers_url`: Verified direct careers page URL (not search string)
    - `domain`: Official company website
    - `linkedin_company_url`: Verified company LinkedIn page
    - `notes_and_fit_rationale`: Tailored explanation of why Sameer's profile matches
- [ ] **Step 2.2: Career URL & Verification Enrichment**
  - Replace Google search placeholders with direct career URLs (e.g., GreenHouse, Lever, Ashby, Workable URLs).

---

### Phase 3: Active Job Ingestion Engine
**Objective:** Scale beyond 41 jobs to 500+ active, verified openings matching Sameer's profile.

- [ ] **Step 3.1: Platform-Specific Extraction Adapters**
  - **Tier 1 (High Quality / Startup & AI Focus):**
    - **Y Combinator (Work at a Startup):** Direct listings in AI, Pune, and India Remote.
    - **Wellfound (formerly AngelList):** Filter for 0-2 YOE, AI/ML Engineer, Full Stack, Pune & India Remote.
    - **Himalayas:** Query remote AI roles with explicit "India" eligibility filter.
    - **Cutshort:** Target active hiring startups in Pune and Bangalore/Remote.
    - **Ashby & Greenhouse direct portals:** Scan career boards of P1 YC & AI startups.
  - **Tier 2 (Ecosystem & Aggregators):**
    - **Hirist / Instahyre:** Python, GenAI, and Backend roles.
    - **We Work Remotely / Working Nomads:** Worldwide remote AI engineering.
    - **LinkedIn Jobs:** Filtered queries for Pune & Remote AI Developer (past 7 days).
- [ ] **Step 3.2: Automated Job Schema**
  - `job_id`: Unique identifier
  - `company_name` & `company_id`
  - `job_title`: (e.g., "Full Stack AI Engineer", "Founding Engineer")
  - `experience_req`: (0-1 yrs, 1-3 yrs, New Grad, etc.)
  - `location`: "Pune", "Remote India", "Remote Worldwide"
  - `salary_or_equity`: Advertised compensation (e.g., ₹12–25 LPA, $80k–$150k)
  - `required_skills`: Extracted tags (`LangGraph`, `RAG`, `Python`, `Playwright`, `FastAPI`)
  - `application_url`: Direct URL to submit resume
  - `posted_date` & `deadline`
  - `source`: Platform name

---

### Phase 4: Candidate-Centric Matching & Scoring Engine
**Objective:** Rank jobs objectively so Sameer applies to the top 10% highest-probability roles first.

- [ ] **Step 4.1: Fit Scoring Matrix (0–100 Score)**
  - **Tech Stack Overlap (40%):**
    - LangGraph / Multi-agent systems / RAG (+25)
    - Python backend (FastAPI / Django / APIs) (+15)
    - AI-native testing / Playwright (+10)
    - Full-stack React / TypeScript / Node (+10)
  - **Experience Alignment (30%):**
    - 0–2 YOE / Junior / Associate / New Grad (+30)
    - 2–3 YOE / Founding Engineer (+20)
    - 4+ YOE / Senior (-15 unless strong domain alignment)
  - **Location & Eligibility (30%):**
    - Pune on-site / hybrid (+30)
    - Remote India confirmed (+30)
    - Worldwide Remote with India accepted (+20)
    - Restrictive US/EU-only (0 / Flagged as Ineligible)
- [ ] **Step 4.2: Automated Classification Tiers**
  - **Tier A (Score 85–100):** Immediate Application + Direct Founder/Recruiter Outreach.
  - **Tier B (Score 70–84):** Standard Application within 48 hours.
  - **Tier C (Score 50–69):** Backlog / Monitor.

---

### Phase 5: Referral & Outreach Intelligence
**Objective:** Never apply "cold" to a P1 company without attempting a referral or direct message.

- [ ] **Step 5.1: Contact Hierarchy per Company Type**
  - **Early-Stage Startups (<50 people):** Founder / CEO / CTO / Founding Engineer.
  - **Mid-Stage & Scale-ups (50–500):** Engineering Manager / Lead AI Engineer / Technical Recruiter.
  - **Large Enterprises / MNCs (>500):** University/Campus Recruiter, Team Lead, College Alumni.
- [ ] **Step 5.2: Tailored Outreach Pitch Templates (Integrated from CV Proof Points)**
  - *Angle 1 (Agentic AI / RAG):* Highlight production LangGraph agents and RAG implementations.
  - *Angle 2 (AI Testing / QA Automation):* Highlight Playwright-based AI test harnesses.
  - *Angle 3 (Full-Stack Product Engineering):* Highlight end-to-end features shipped from UI to DB.
- [ ] **Step 5.3: Verified Contacts Database**
  - Scale beyond the 4 current verified people by enriching top 100 P1 companies with verified LinkedIn profile handles and corporate email formats (`first@company.com`).

---

### Phase 6: Application Pipeline & Daily Execution CRM
**Objective:** A streamlined workflow that lets Sameer apply to 10–15 curated jobs every day without friction.

- [ ] **Step 6.1: Pipeline Kanban Stages**
  1. `Discovered` (Score > 75)
  2. `Referral Sourced` (Message sent to employee/recruiter)
  3. `Applied Directly` (Application submitted via portal)
  4. `Followed Up` (7-day follow-up sent)
  5. `Screening / OA` (Online Assessment / Recruiter Call)
  6. `Technical Interview`
  7. `Final / Offer`
- [ ] **Step 6.2: Daily Application Targets**
  - **Daily Goal:** 10 applications (3 Tier-A with referral outreach, 7 Tier-B portal applications).
  - **Weekly Review:** Track response rates by platform and adjust targeting.

---

## 4. Immediate Next Steps & Milestones

1. **Clean Workspace & Reclaim Storage:** Archive redundant `(1).csv`, `(2).csv` files and redundant 31-job CSVs.
2. **Build Unified Master Company Directory:** Merge all 2,056 unique companies into `master_companies_database.csv`, restoring the 692 dropped records.
3. **Build the Clean Jobs Hub:** Consolidate the 41 existing verified jobs into an application-ready format.
4. **Implement Platform Extractors:** Run targeted queries for YC, Wellfound, and Himalayas to scale active openings to 100+ verified listings.
