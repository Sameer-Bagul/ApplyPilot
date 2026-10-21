# **Autonomous Self-Evolving AI Job Application Agent & MCP System: Master Architecture, Feature Guide & Agent Build Specification**

# **1\. System Overview and Architectural Vision**

Modern automated job application systems fail in production for three primary reasons: brittle browser automation that breaks across diverse Applicant Tracking Systems (ATS), high token consumption from repeatedly sending full DOM snapshots to Large Language Models (LLMs), and silent hallucinations when agents encounter unfamiliar screening questions or authentication barriers. This specification defines an end-to-end, self-evolving autonomous job application platform and Model Context Protocol (MCP) server built by extending the open-source foundation of [ibarrajo/ApplyPilot](https://github.com/ibarrajo/ApplyPilot) (itself an enhanced fork of [Pickle-Pixel/ApplyPilot](https://github.com/Pickle-Pixel/ApplyPilot)) alongside [Playwright MCP, JobSpy, Browser Use, Skyvern, HumanLayer, and LangGraph Interrupts.](https://github.com/microsoft/playwright-mcp)

[The system is architected around three core pillars](https://github.com/microsoft/playwright-mcp):

1. **Universal MCP & Multi-Provider Interoperability:** Every capability—job discovery, resume tailoring, candidate knowledge retrieval, deterministic browser replay, and asynchronous human escalation—is exposed as a standardized MCP tool. Any MCP-compatible coding agent (such as Claude Code, Cursor, or custom [LangGraph](https://docs.langchain.com/oss/python/langgraph/interrupts) orchestrators) or LLM provider API (Gemini, OpenAI, Anthropic, or local Ollama models) can drive the pipeline.  
2. **Asynchronous Email Human-in-the-Loop (HITL) with State Re-Hydration:** Whenever the agent encounters an out-of-scope screening question, an unsolved CAPTCHA, or a non-email Multi-Factor Authentication (2FA) prompt, it never guesses or fabricates data. Instead, it serializes the form state, closes the browser worker to save memory, and dispatches a structured email via the Gmail API or [HumanLayer](https://github.com/humanlayer/humanlayer). Once the user replies via email, the system parses the reply, permanently updates the candidate knowledge base, re-hydrates the browser session, and finishes the application automatically.  
3. **Self-Evolving Zero-Token Progression Loop:** Rather than invoking an expensive LLM on every form field indefinitely, the platform treats the LLM as a *compiler* that teaches deterministic Playwright scripts how to fill forms. After each run, a pattern-consolidation engine extracts successful DOM selectors, dropdown mappings, and normalized question-answer pairs into a local SQLite and vector store (`applypilot.db`). Subsequent applications on the same ATS (Workday, Greenhouse, Lever, Ashby, SmartRecruiters, iCIMS) execute via Tier 0 deterministic replay and Tier 1 local semantic matching, reducing LLM token expenditure by 80% to 95% over time.

| Architectural Layer | Base Open-Source Component | Role in the Self-Evolving Pipeline |
| :---- | :---- | :---- |
| **Core Pipeline & CLI** | [ibarrajo/ApplyPilot](https://github.com/ibarrajo/ApplyPilot) / [Pickle-Pixel/ApplyPilot](https://github.com/Pickle-Pixel/ApplyPilot) | Provides the 6-stage job pipeline (`discover`, `enrich`, `score`, `tailor`, `apply`, `track`), SQLite storage (`applypilot.db`), ATS cookie vault, and Q\&A store. |
| **Multi-Board Discovery** | [JobSpy](https://github.com/speedyapply/JobSpy) ([README](https://github.com/cullenwatson/jobspy/blob/main/README.md)) | Scrapes LinkedIn, Indeed, Glassdoor, ZipRecruiter, Google Jobs, and Naukri concurrently into normalized job schemas. |
| **Browser Execution & MCP** | [Playwright MCP](https://github.com/microsoft/playwright-mcp) ([Docs](https://playwright.dev/docs/getting-started-mcp)) & [Browser Use](https://github.com/browser-use/browser-use) | Exposes accessibility-tree snapshots and deterministic DOM actions (`click`, `fill`, `select_option`, `upload_file`) to MCP clients. |
| **Visual Fallback Engine** | [Skyvern](https://github.com/skyvern-ai/skyvern) ([Jobs Agent](https://www.skyvern.com/blog/launching-skyverns-jobs-agent-automate-job-applications-with-ai-2/)) | Optional vision-LLM fallback for obfuscated Shadow DOM or canvas-based enterprise portals where accessibility trees fail. |
| **Asynchronous HITL & State** | Gmail OAuth API & [HumanLayer](https://github.com/humanlayer/humanlayer) & [LangGraph Interrupts](https://reference.langchain.com/python/langgraph/types/interrupt) | Checkpoints agent execution state, sends structured clarification emails, ingests user replies, and resumes parked applications. |

# **2\. End-to-End User Flow**

The user experience is designed for "configure once, supervise via inbox." After initial setup, the user interacts with the agent almost exclusively through email replies when novel questions arise.

## **Phase A: Initial Onboarding & Seed Knowledge Pool**

1. **Profile & Resume Initialization:** The user populates `config.yaml` (target roles, locations, remote preferences, minimum match score threshold, blacklisted companies) and `profile.json` (structured personal identity, work history, education, skills, links, work authorization, and baseline compensation expectations), and places a master LaTeX or PDF resume in `resumes/`.  
2. **Gmail OAuth Handshake:** The user executes `python scripts/gmail_oauth.py` once to generate OAuth2 tokens (`~/.gmail-mcp/credentials.json`) with `gmail.send`, `gmail.readonly`, and `gmail.modify` scopes. This single connection powers three subsystems: sending HITL clarification emails, intercepting automated ATS verification/OTP codes, and tracking post-application recruiter responses.  
3. **Seed Q\&A Import:** The user optionally runs `applypilot qa import seed_qa.yaml` to pre-load common screening answers (notice period, sponsorship status, willingness to relocate, demographic/EEO preferences).

## **Phase B: Autonomous Daily Run (Unattended Execution)**

1. **Scheduled or Manual Trigger:** A cron daemon or MCP client runs `applypilot run --daemon` (or invokes the MCP `run_pipeline_cycle` tool).  
2. **Silent Execution of Known Patterns:** For jobs whose application forms match previously learned ATS playbooks and known Q\&A entries, the agent scores the job, compiles a tailored PDF resume, fills the entire application via cached Playwright selectors, submits the form, captures a confirmation screenshot, and logs the status as `applied`—consuming zero LLM tokens for form navigation.

## **Phase C: Encountering an Unknown Question or Edge Case (The Email HITL Loop)**

1. **Detection & Batching:** Suppose the agent reaches page 3 of a Greenhouse or Workday application and finds two questions not covered in `profile.json` or `qa_knowledge_base`: *"Describe a time you reduced cloud infrastructure costs"* and *"Are you available to work overlapping hours with IST and EST?"* Rather than stopping at the first unknown field, the agent inspects the entire current form page (and any accessible steps) to batch all unknown questions into a single request.  
2. **Draft Preservation & Parking:** If the portal supports "Save Draft" (such as Workday), the agent clicks it. It also serializes all filled field values, the exact page URL, the ATS session cookies, and the list of missing questions into a `hitl_tickets` record in `applypilot.db`, marks the job as `parked_awaiting_email`, and closes the Playwright browser tab.  
3. **Outbound Clarification Email:** The agent sends an email to the user with the subject `[ApplyPilot HITL #1042] Action Needed: Senior Backend Engineer at Acme Corp (2 Questions)`. The email contains:  
   * Job title, company name, match score, compensation range, and direct job URL.  
   * Numbered questions with field constraints (e.g., `[Q1 - Dropdown: Yes / No]`, `[Q2 - Textarea, max 500 chars]`, plus an optional LLM-suggested draft answer for open-ended essays that the user can approve with `APPROVE Q2` or override).  
   * Simple reply instructions so the user can reply inline from their phone.  
4. **Inbound Reply Processing & Knowledge Expansion:** When the user replies to the email, the Gmail polling worker (`applypilot track --poll-hitl`) detects the thread reply, extracts the answers, validates them against the field constraints (e.g., ensuring a dropdown reply matches one of the valid options), writes the canonicalized Q\&A pair into `qa_knowledge_base`, and flips the job status from `parked_awaiting_email` to `queued_resume`.  
5. **Automatic Re-Hydration & Submission:** On the next worker tick, Playwright opens the job URL with the saved ATS cookies, replays all cached field values in milliseconds, injects the newly learned answers, submits the application, and emails/logs the final confirmation receipt.

# **3\. Feature Flow and 7-Stage Pipeline Architecture**

Building on the 6-stage pipeline of [ibarrajo/ApplyPilot](https://github.com/ibarrajo/ApplyPilot), the system introduces a 7th stage (learn) that closes the self-evolving feedback loop.

| Stage | Command / MCP Tool | Input | Processing Logic | Output & State Transition |
| :---- | :---- | :---- | :---- | :---- |
| **1\. Discover** | `applypilot discover` | `config.yaml` search queries & board targets | Runs [JobSpy](https://github.com/speedyapply/JobSpy), Hacker News Who's Hiring scraper, Workday portal crawlers, and Greenhouse/Lever board feeds; deduplicates by `(company_norm, title_norm)` and canonical URL. | Inserts new records into `jobs` table with `status = 'discovered'`. |
| **2\. Enrich** | `applypilot enrich` | `jobs` where `status = 'discovered'` | Fetches full job descriptions via lightweight HTTP/Playwright requests; extracts structured metadata (tech stack, visa sponsorship flags, seniority, salary bands) via regex heuristics first, falling back to Flash LLM only if unstructured. | Updates `jobs.description` and `jobs.extracted_requirements`; sets `status = 'enriched'`. |
| **3\. Score** | `applypilot score` | `jobs` where `status = 'enriched'` \+ `profile.json` | Evaluates candidate-job fit (0–100) using a deterministic rubric pre-filter (hard killers: required clearance, incompatible location, missing mandatory license) before invoking the LLM scorer. | Sets `jobs.score`; jobs above threshold move to `status = 'shortlisted'`, others to `status = 'rejected_score'`. |
| **4\. Tailor** | `applypilot tailor` | `jobs` where `status = 'shortlisted'` \+ Master Resume | Selects relevant bullet variants from a pre-approved achievement library or rewrites bullets in LaTeX/DOCX without fabricating skills; compiles PDF to `output/tailored/<job_id>.pdf`. | Stores PDF path in `jobs.resume_path`; sets `status = 'ready_to_apply'`. |
| **5\. Apply** | `applypilot apply` | `jobs` where `status IN ('ready_to_apply', 'queued_resume')` | Executes Tier 0 cached ATS playbook first; uses Tier 1 local Q\&A semantic lookup for screening fields; invokes Tier 3 LLM only on unmapped DOM nodes; triggers Tier 4 Email HITL if blocked. | Transitions to `status = 'applied'` (on confirmation) or `status = 'parked_awaiting_email'` (on HITL). |
| **6\. Track** | `applypilot track` | Gmail API (`~/.gmail-mcp/`) \+ `hitl_tickets` | Scans inbox for (a) user replies to `[ApplyPilot HITL #ID]` threads, (b) ATS verification/OTP codes, and (c) recruiter emails (confirmations, assessments, interviews, rejections). | Updates `qa_knowledge_base`, unlocks parked jobs (`queued_resume`), and updates application lifecycle states. |
| **7\. Learn** | `applypilot learn` | Execution telemetry logs from Stage 5 (`apply_trace.jsonl`) | Analyzes every field where an LLM was required during Stage 5; synthesizes reusable CSS/ARIA selectors, label regexes, and canonical Q\&A mappings; promotes verified patterns to Tier 0/Tier 1 caches. | Writes new rules to `ats_selector_cache` and `pattern_rules`, shrinking future token usage. |

# **4\. The Self-Evolving, Token-Minimizing Engine (Zero-Token Progression)**

To prevent the agent from spending thousands of LLM tokens re-reading identical Workday, Greenhouse, or Lever forms on every single application, all form interactions are routed through a strict 5-Tier Resolution Cascade. Higher tiers are only invoked when lower tiers return a cache miss.\[Incoming Form Page / Field\]

       │

       ▼

┌──────────────────────────────────────────────────────────┐

│ TIER 0: Deterministic ATS Playbook & Selector Cache      │ \-\> (0 Tokens, \~15ms)

│ Matches ATS domain \+ page signature \-\> Direct Playwright │

└──────────────────────────┬───────────────────────────────┘

                           │ Cache Miss

                           ▼

┌──────────────────────────────────────────────────────────┐

│ TIER 1: Canonical Q\&A Hash & Local Embedding Retriever   │ \-\> (0 API Tokens, \~40ms)

│ Normalizes label text \+ SQLite FTS5 / Local ONNX Vector  │

└──────────────────────────┬───────────────────────────────┘

                           │ Similarity \< 0.90

                           ▼

┌──────────────────────────────────────────────────────────┐

│ TIER 2: Learned Heuristic & Regex Rule Engine            │ \-\> (0 Tokens, \~5ms)

│ Applies post-run synthesized rules (dates, numbers, URLs)│

└──────────────────────────┬───────────────────────────────┘

                           │ No Rule Match

                           ▼

┌──────────────────────────────────────────────────────────┐

│ TIER 3: Compact Accessibility-Tree Flash LLM Inference   │ \-\> (\~300–800 Tokens)

│ Sends pruned field neighborhood (not full HTML) to LLM   │

└──────────────────────────┬───────────────────────────────┘

                           │ Confidence \< 0.85 or Restricted Topic

                           ▼

┌──────────────────────────────────────────────────────────┐

│ TIER 4: Asynchronous Email HITL Escalation               │ \-\> (0 Hallucinations)

│ Parks job, emails user, ingests reply \-\> Promotes to T1  │

└──────────────────────────────────────────────────────────┘

## **How Pattern Gathering and Promotion Works After Each Run**

1. **Accessibility-Tree Neighborhood Pruning (Immediate 85% Token Cut When LLM Is Needed):** When a novel page is encountered, the system never sends raw HTML to the LLM. Using [Playwright MCP](https://github.com/microsoft/playwright-mcp)'s accessibility snapshot or DOM distiller, it strips all `<script>`, `<style>`, SVG paths, and layout wrappers, extracting only interactive form controls (`input`, `select`, `textarea`, `button`, `role="combobox"`) along with their associated `<label>`, `aria-label`, `placeholder`, and validation error nodes.  
2. **Trace Recording (`apply_trace.jsonl`):** Whenever Tier 3 (the LLM) successfully maps a form element (for example, determining that `input[data-automation-id="legalNameSection_firstName"]` on `*.myworkdayjobs.com` maps to `profile.first_name`), the worker records an immutable trace entry containing `(ats_type, url_pattern, dom_selector, aria_role, label_text, mapped_profile_key, validation_passed)`.  
3. **Post-Run Promotion (`applypilot learn`):** At the end of each batch—only for applications where the page transition or final submission succeeded without validation errors—the learning engine promotes those trace entries into `ats_selector_cache`. The next time the agent visits *any* Workday portal, Tier 0 immediately fills `input[data-automation-id="legalNameSection_firstName"]` using pure Python Playwright without calling any LLM.  
4. **Dropdown Option Canonicalization:** Dropdown menus (such as *"Country"*, *"Highest Degree Attained"*, or *"How did you hear about us?"*) vary slightly in wording across employers (`"Bachelor's Degree"` vs. `"B.S. / B.A."` vs. `"Undergraduate (4-Year)"`). Whenever the LLM or human selects an option for a canonical question, the selected option string is appended to a synonym array in `qa_knowledge_base.option_synonyms`. Future dropdowns are matched via deterministic fuzzy string matching (`rapidfuzz` score \>= 92\) at zero token cost.  
5. **Failure Demotion (Self-Healing Cache):** If an ATS updates its frontend and a cached Tier 0 selector throws a `TimeoutError` or triggers a red client-side validation message, the agent increments `failure_count` on that `ats_selector_cache` row, seamlessly falls back to Tier 3 LLM resolution for that single element, and overwrites the stale selector once the new mapping succeeds.

# **5\. System Design and Database Schema (`applypilot.db`)**

All state is stored locally in SQLite (`~/.applypilot/applypilot.db`) with WAL (Write-Ahead Logging) enabled for safe concurrent access by parallel Playwright workers, the MCP server, and the Gmail background poller.

| Table Name | Primary Key | Key Columns & Schema Purpose |
| :---- | :---- | :---- |
| `jobs` | `job_id` (TEXT) | `company`, `title`, `board_source`, `apply_url`, `ats_type`, `status` (`discovered`, `enriched`, `shortlisted`, `ready_to_apply`, `parked_awaiting_email`, `queued_resume`, `applied`, `failed_permanent`), `score`, `resume_path`, `retry_count`, `last_error`. |
| `qa_knowledge_base` | `qa_id` (INTEGER) | `canonical_question` (TEXT), `question_hash` (TEXT UNIQUE), `embedding_blob` (BLOB, local 384-dim ONNX vector), `field_type` (`text`, `number`, `select`, `radio`, `checkbox`, `file`), `answer_value` (TEXT), `option_synonyms` (JSON array), `category` (`compensation`, `work_auth`, `experience_years`, `behavioral`, `eeo`), `source` (`seed`, `llm_inferred`, `human_email`), `use_count` (INT). |
| `ats_selector_cache` | `selector_id` (INTEGER) | `ats_type` (`workday`, `greenhouse`, `lever`, `ashby`, `smartrecruiters`, `icims`, `custom_domain`), `domain_pattern` (TEXT), `step_signature` (TEXT), `css_or_aria_selector` (TEXT), `action_type` (`fill`, `select`, `click`, `upload`, `combobox_typeahead`), `target_key` (references `profile.json` path or `qa_id`), `success_count` (INT), `failure_count` (INT), `last_verified_at` (TIMESTAMP). |
| `hitl_tickets` | `ticket_id` (INTEGER) | `job_id` (TEXT FK), `gmail_thread_id` (TEXT), `gmail_message_id` (TEXT), `status` (`sent`, `replied`, `parsed`, `expired`), `unanswered_questions_json` (JSON array of `{field_id, label, field_type, options, required, max_length, suggested_draft}`), `dom_checkpoint_json` (JSON snapshot of already-filled fields & page URL), `created_at`, `resolved_at`. |
| `ats_session_vault` | `vault_id` (INTEGER) | `ats_type` (TEXT), `company_domain` (TEXT), `storage_state_path` (TEXT path to encrypted Playwright `state.json` cookies/localStorage), `account_email` (TEXT), `last_login_at` (TIMESTAMP), `session_valid` (BOOLEAN). |
| `pattern_rules` | `rule_id` (INTEGER) | `rule_name` (TEXT), `label_regex` (TEXT), `field_type` (TEXT), `transform_expression` (TEXT, e.g., converting `profile.experience_years * 12` when a label asks for experience in months), `confidence` (REAL), `hit_count` (INT). |

# **6\. MCP Server Specification (`applypilot-mcp`)**

To allow any external coding agent (Claude Code, Cursor, Windsurf, Cline) or custom orchestrator to control or inspect the job application engine, the repository exposes a FastMCP server (src/applypilot/mcp\_server.py). It operates alongside or wraps [Playwright MCP](https://github.com/microsoft/playwright-mcp).

| MCP Tool Name | Input Parameters | Output Payload | Agent Usage Context |
| :---- | :---- | :---- | :---- |
| `discover_and_score_jobs` | `roles: list[str]`, `locations: list[str]`, `min_score: int`, `max_results: int` | List of shortlisted jobs with `job_id`, `score`, `ats_type`, and missing skill gaps. | Called by an agent to populate the queue with high-fit job openings. |
| `resolve_form_fields` | `ats_type: str`, `url: str`, `fields: list[{id, label, type, options}]` | Mapped values for each `field.id` with `resolution_tier` (`0..2`), plus a list of `unresolved_fields` requiring Tier 3/4. | Called before invoking an LLM on a form page so 80–95% of fields are resolved deterministically at 0 token cost. |
| `record_learned_mapping` | `ats_type: str`, `url_pattern: str`, `selector: str`, `label: str`, `profile_or_qa_key: str` | `{status: "cached", selector_id: int}` | Called by the browser-driving agent after successfully submitting a page so future runs bypass the LLM. |
| `escalate_to_email_hitl` | `job_id: str`, `current_url: str`, `unanswered_questions: list[dict]`, `filled_state: dict`, `reason: str` | `{ticket_id: int, gmail_thread_id: str, job_status: "parked_awaiting_email"}` | Called whenever confidence \< 0.85, an out-of-scope question appears, or a hard blocker (CAPTCHA/SMS 2FA) occurs. |
| `sync_email_hitl_replies` | `poll_window_hours: int` | `{resolved_tickets: list[int], newly_learned_qa_count: int, requeued_jobs: list[str]}` | Polls Gmail for user replies to HITL emails, updates `qa_knowledge_base`, and re-queues parked jobs. |
| `fetch_ats_otp_code` | `company_domain: str`, `sender_hint: str`, `wait_seconds: int` | `{otp_code: str | null, magic_link: str | null}` | Automatically retrieves 6-digit verification codes or activation links sent to the user's Gmail during Workday/iCIMS account creation. |

# **7\. Exhaustive Edge-Case Matrix and HITL Recovery Protocols**

A production auto-applier must anticipate every failure mode across messy enterprise career portals and degrade gracefully to the human-in-the-loop without corrupting applications or submitting false legal/personal statements.

| Edge Case Category | Specific Failure Scenario | Automated Mitigation & Detection Mechanism | HITL Escalation & Self-Learning Recovery |
| :---- | :---- | :---- | :---- |
| **1\. Out-of-Scope Screening Questions** | Form asks a novel factual question (e.g., *"Do you have active security clearance?"*, *"What was your GPA in high school?"*) or a role-specific essay not in `profile.json`. | **Strict Non-Fabrication Guardrail:** Fields matching sensitive categories (visa/legal status, criminal/background checks, licenses, clearances, binding salary minimums) have a hard rule: `allow_llm_guess = False`. If Tier 1 semantic similarity \< 0.90, execution halts after scanning the rest of the page. | Dispatches batched `[ApplyPilot HITL #ID]` email. For open-ended behavioral essays, Tier 3 generates a draft grounded *only* in `profile.json` and includes it in the email so the user can either reply `APPROVE` or send a custom edit. Answer is saved to `qa_knowledge_base`. |
| **2\. Browser Session Expiry During Email Wait** | User takes 6 hours to reply to the HITL email; the ATS webpage timed out after 20 minutes of inactivity. | **Stateless Checkpoint & Draft Save:** The agent never holds a live browser open while waiting for an email. Before parking, it (1) clicks native "Save Draft" if present, (2) saves cookies to `ats_session_vault`, and (3) saves `dom_checkpoint_json` (all filled key-value pairs per step) in `hitl_tickets`. | When the email reply arrives, a fresh worker loads the URL, restores cookies, fast-forwards through Steps 1..N using `dom_checkpoint_json` \+ Tier 0 selectors in \<3 seconds, fills the new answer, and submits. |
| **3\. Account Creation & Email OTP / Magic Links** | Workday, iCIMS, or Taleo forces candidate registration and sends a 6-digit OTP code or verification link to the user's email before allowing form entry. | **Deterministic Account Vault \+ Gmail OTP Interceptor:** The agent registers using the candidate's email and a deterministic per-domain password stored in local OS keyring / `ats_session_vault`. It then calls `fetch_ats_otp_code` to poll Gmail for 60 seconds, extracts the OTP or verification URL via regex, and completes verification autonomously. | If the portal requires **SMS/Authenticator 2FA** instead of email, `escalate_to_email_hitl` sends a high-priority notification with a local/Tailscale VNC or `localhost:7373` one-click session handoff link. |
| **4\. CAPTCHAs & Anti-Bot Firewalls** | Cloudflare Turnstile, hCaptcha, or Google reCAPTCHA v2/v3 blocks page load or final submission. | **Persistent Stealth Contexts:** Workers run with persistent user-data directories (`~/.applypilot/browser-profiles/<ats_type>`) and realistic viewport/fingerprint settings rather than fresh incognito contexts, preserving trust cookies across runs. | If a hard CAPTCHA challenge appears (`iframe[src*="recaptcha"]`, `cf-turnstile`), the worker captures a screenshot, parks the job (`parked_captcha`), and emails the user a deep link to resolve the challenge in the persistent browser profile once; the resulting clearance cookie is reused for subsequent jobs. |
| **5\. Workday "Resume Auto-Fill" Corruption** | Uploading a resume on Step 1 of Workday triggers an internal parser that overwrites Step 2 work history fields with mangled dates or split bullet points. | **Post-Upload Verification Pass:** After any file upload on Workday/Taleo, the agent waits for the parsing spinner to disappear, then explicitly inspects every populated Work Experience and Education container against `profile.json`, overwriting corrupted dates, titles, or descriptions with clean profile strings. | Learned field selectors for the "Work Experience \#1..N" repeater blocks are stored in `ats_selector_cache` so the verification pass runs deterministically at 0 tokens. |
| **6\. Dynamic Conditional Fields & React Comboboxes** | Selecting `"Yes"` on a radio button (e.g., *"Were you referred by an employee?"* or *"Do you need sponsorship?"*) dynamically mounts a new required input field into the DOM; or location fields require selecting from an async typeahead dropdown. | **MutationObserver Stabilization & Combobox Protocol:** After every `click` or `select` action, the Playwright wrapper waits 300ms for DOM mutations and re-scans for newly visible `[required]` or `aria-required="true"` elements before clicking "Next". For `role="combobox"`, it types the city name, waits for `role="listbox"` options, and selects the closest match via `rapidfuzz`. | If a newly revealed conditional field cannot be answered from `qa_knowledge_base`, it is appended to the current page's HITL question batch before parking. |
| **7\. Client-Side Validation Errors on "Next / Submit"** | Clicking "Next" or "Submit" does not advance the page because a field failed format validation (e.g., phone number requires `+91-XXXXXXXXXX` vs `10 digits`, or GPA requires a `4.0` scale). | **Post-Click Error Scraper:** If the URL or step header does not change within 3 seconds of clicking "Next/Submit", the agent scrapes all visible elements matching `[aria-invalid="true"]`, `.error`, `[data-automation-id*="error"]`, or red text adjacent to inputs. | Passes the exact error message \+ field label to Tier 2/Tier 3 to reformat the value (e.g., reformatting phone/GPA scale) and saves the format rule in `pattern_rules`. If still rejected after 1 retry, escalates via Email HITL with a screenshot of the error. |
| **8\. Ambiguous / Non- Matching Dropdown Options** | Form asks *"Notice Period"* with options `["Immediate", "15 Days", "30 Days", "60+ Days"]`, while user's profile says `"3 weeks (21 days)"`. | **Conservative Boundary Rule:** Numeric range dropdowns use a deterministic boundary mapper (e.g., rounding notice period *up* to the nearest bucket that the candidate can realistically honor, or matching degree level). If options are semantically ambiguous, the agent does not guess. | Emails the user the exact dropdown options (`1: Immediate, 2: 15 Days, 3: 30 Days, 4: 60+ Days`) so the user can reply with `3`, then maps `"30 Days"` as the approved synonym for future 21-to-30-day dropdowns. |
| **9\. Duplicate Postings & Re-Application Prevention** | The same role is scraped from LinkedIn, Indeed, and the company's direct Greenhouse board, or the user already applied 2 weeks ago. | **3-Layer Deduplication Guard:** Before Stage 3 (`score`) and Stage 5 (`apply`), the system checks (1) exact normalized apply URL, (2) `(normalized_company, normalized_title, location)` fuzzy hash within 60 days, and (3) ATS portal banner detection (if the page displays *"You have already applied to this position"*, immediately mark `applied_previously` and abort). | Zero tokens wasted; logs duplicate link to the primary `job_id`. |
| **10\. Ambiguous Reply in User's HITL Email** | User replies to a 3-question HITL email, but skips Question 2 or gives an answer that violates field constraints (e.g., 800 characters for a 300-character field). | **Inbound Reply Validator:** The email parser validates each extracted answer against `unanswered_questions_json` (checking required presence, numeric type, max character length, or dropdown option membership). | If an answer violates constraints, the agent auto-replies to the same email thread explaining the specific constraint (or offering a trimmed 295-character version for one-word confirmation) while saving the valid answers right away. |

# **8\. Detailed Email HITL Wireframe and Reply Protocol**

To make email interaction effortless on mobile or desktop without requiring a custom web app, the email protocol uses deterministic thread tags and a lightweight human-friendly syntax.

## **Outbound Email Template (`src/applypilot/hitl/email_notifier.py`)**

**Subject:** `[ApplyPilot HITL #1042] 2 Questions — Senior AI Engineer @ Acme Corp (Score: 91/100)`

**Job Summary:** Senior AI Engineer at Acme Corp (Remote / Bengaluru)Portal: Greenhouse (https\://boards.greenhouse.io/acmecorp/jobs/4920192)Progress: 14 of 16 fields auto-filled at 0 LLM tokens (Tier 0/1 cache). Application paused on Step 1\.**Questions Requiring Your Input:**

**Q1 \[Required | Dropdown\]**  
*Label:* "Are you legally authorized to work in India and willing to attend quarterly in-person sprints in Pune?"  
*Options:*  
`A)` Yes, authorized and available for quarterly travel  
`B)` Authorized, but require 100% remote with no travel  
`C)` Require sponsorship

**Q2 \[Required | Short Text — Max 250 chars\]**  
*Label:* "Link to a production MCP server or AI agent repository you have built or contributed to:"  
*Suggested Draft (from profile.json):* `https://github.com/sameer/mcp-agent — Built an autonomous Playwright + RAG agent workflow.`

**How to Reply:**  
Simply reply to this email with your answers by question number (for example: `Q1: A` and `Q2: APPROVE` or write your custom text for Q2). Your answers will be saved to your permanent Knowledge Base and the application will submit automatically.

## **Inbound Email Parser Logic (`src/applypilot/hitl/email_reply_parser.py`)**

1. **Zero-Token Regex Parser First:** The parser strips quoted email history (lines starting with `>` or following `On ... wrote:`) and applies a deterministic regex for `Q(\d+)\s*[:\-]\s*(.+)` blocks.  
   * If `Q1: A` is matched on a dropdown question, it maps `A` directly to option index `0` (`"Yes, authorized and available for quarterly travel"`).  
   * If `Q2: APPROVE` is matched, it promotes the `suggested_draft` as the verified answer.  
2. **Flash LLM Fallback for Natural Prose Replies:** If the user replies conversationally (e.g., *"Yes to the first one, and for the second one just use my main GitHub profile link instead"*), a lightweight Flash LLM call maps the user's natural language onto the structured `unanswered_questions_json` schema.  
3. **Permanent Promotion:** Each resolved question is hashed (`sha256(normalize_label(label))`), embedded via a local sentence-transformer (`all-MiniLM-L6-v2` running on CPU at 0 API cost), and upserted into `qa_knowledge_base` with `source = 'human_email'`.

# **9\. Implementation Blueprint & File-by-File Guide for Coding Agents**

This section serves as the direct implementation prompt and file manifest for an AI coding agent (such as Claude Code or Cursor) tasked with building the system on top of [ibarrajo/ApplyPilot](https://github.com/ibarrajo/ApplyPilot).

## **Repository Directory Layout**

applypilot/

├── config.example.yaml                 \# Search criteria, LLM provider cascade, HITL email toggle

├── profile.example.json                \# Structured candidate source-of-truth

├── scripts/

│   └── gmail\_oauth.py                  \# Existing OAuth setup (ensure gmail.send \+ gmail.modify scopes)

└── src/applypilot/

    ├── cli.py                          \# CLI entrypoints: discover, enrich, score, tailor, apply, track, learn, mcp

    ├── config.py                       \# Pydantic settings & environment loader

    ├── db/

    │   ├── schema.py                   \# SQLite tables: jobs, qa\_knowledge\_base, ats\_selector\_cache, hitl\_tickets, pattern\_rules

    │   └── repository.py               \# CRUD operations \+ WAL mode concurrency helpers

    ├── mcp\_server.py                   \# NEW: FastMCP server exposing pipeline, knowledge, and HITL tools

    ├── learning/

    │   ├── tier0\_playbook.py           \# NEW: Deterministic Playwright selector replay per ATS domain

    │   ├── tier1\_semantic\_qa.py        \# NEW: Canonical label normalizer \+ FTS5 \+ local ONNX cosine matcher

    │   ├── tier2\_heuristics.py         \# NEW: Regex rules for dates, phone formatting, unit conversions, dropdown fuzzy match

    │   └── pattern\_compiler.py         \# NEW: Stage 7 (\`applypilot learn\`) trace analyzer & cache promoter

    ├── hitl/

    │   ├── email\_notifier.py           \# NEW: Sends batched \[ApplyPilot HITL \#ID\] emails via Gmail API

    │   ├── email\_reply\_parser.py       \# NEW: Polls Gmail replies, validates constraints, updates QA DB, requeues jobs

    │   ├── otp\_interceptor.py          \# NEW: Fetches 6-digit ATS verification codes & magic links from Gmail

    │   └── checkpoint.py               \# NEW: Serializes/restores DOM field states & ATS storage\_state cookies

    └── pipeline/

        ├── discover.py                 \# Stage 1: JobSpy \+ HN \+ Workday \+ Greenhouse/Lever scrapers

        ├── enrich.py                   \# Stage 2: Description fetcher & heuristic metadata extractor

        ├── score.py                    \# Stage 3: Hard-killer rubric pre-filter \+ LLM fit scoring

        ├── tailor.py                   \# Stage 4: Resume bullet selector & PDF compiler

        ├── apply.py                    \# Stage 5: Orchestrates Tier 0-\>4 cascade \+ Playwright MCP worker

        └── track.py                    \# Stage 6: Unified Gmail scanner (recruiter updates \+ HITL replies)

## **Step-by-Step Build Instructions for the Coding Agent**

When feeding this specification to a coding agent, instruct it to execute the build in the following five verified milestones:

### **Milestone 1: Clone Base Repository & Upgrade SQLite Schema**

1. Clone [ibarrajo/ApplyPilot](https://github.com/ibarrajo/ApplyPilot) and create a Python 3.11+ virtual environment.  
2. Extend `src/applypilot/db/schema.py` to add `ats_selector_cache`, `hitl_tickets`, `ats_session_vault`, and `pattern_rules`, and add `embedding_blob`, `option_synonyms`, and `source` columns to `qa_knowledge_base`.  
3. Write unit tests in `tests/test_db_schema.py` verifying idempotent schema migrations and concurrent WAL reads/writes.

### **Milestone 2: Build the Tier 0–2 Zero-Token Resolution Engine**

1. Implement `src/applypilot/learning/tier1_semantic_qa.py` with a canonical question normalizer (lowercasing, stripping punctuation/stopwords, mapping common synonyms like `"compensation"` \-\> `"salary"` and `"sponsorship"` \-\> `"visa"`) backed by SQLite FTS5 and `rapidfuzz` dropdown matching.  
2. Implement `src/applypilot/learning/tier0_playbook.py` to store and execute verified `(ats_type, step_signature, css_or_aria_selector, action_type, target_key)` records directly via Playwright before any LLM is invoked.  
3. Implement `src/applypilot/learning/pattern_compiler.py` (`applypilot learn`) to read successful execution traces from `logs/apply_trace.jsonl` and promote selectors with `validation_passed == True` into `ats_selector_cache`.

### **Milestone 3: Implement the Asynchronous Email HITL & OTP Loop**

1. Update `scripts/gmail_oauth.py` to request `https://www.googleapis.com/auth/gmail.send`, `https://www.googleapis.com/auth/gmail.readonly`, and `https://www.googleapis.com/auth/gmail.modify`.  
2. Implement `src/applypilot/hitl/email_notifier.py` and hook it into `_run_hitl` inside `src/applypilot/pipeline/apply.py` so that whenever `--hitl-mode email` is active and an unresolvable field or CAPTCHA is encountered, the worker batches all unknown fields on the current step, snapshots `dom_checkpoint_json`, creates a `hitl_tickets` entry, sends the `[ApplyPilot HITL #<ticket_id>]` email, and parks the job cleanly.  
3. Implement `src/applypilot/hitl/email_reply_parser.py` and integrate it into `src/applypilot/pipeline/track.py` so running `applypilot track` processes user replies, validates constraints, inserts new facts into `qa_knowledge_base`, and flips parked jobs to `queued_resume`.  
4. Implement `src/applypilot/hitl/otp_interceptor.py` to automatically extract ATS registration verification codes from Gmail during Workday/iCIMS sign-ups.

### **Milestone 4: Expose the FastMCP Server (`applypilot-mcp`)**

1. Implement `src/applypilot/mcp_server.py` using the official Python `mcp` SDK (`FastMCP`), registering the six core tools (`discover_and_score_jobs`, `resolve_form_fields`, `record_learned_mapping`, `escalate_to_email_hitl`, `sync_email_hitl_replies`, `fetch_ats_otp_code`).  
2. Add the `applypilot mcp` CLI command in `src/applypilot/cli.py` so any MCP host (Claude Desktop, Claude Code, Cursor, or custom agent) can attach via `stdio` or `sse`.

### **Milestone 5: End-to-End Dry Run & Self-Learning Benchmark**

1. Run a 5-job dry-run test (`applypilot apply --dry-run --hitl-mode email`) against sample Greenhouse, Lever, and Workday forms (where `--dry-run` fills all steps and captures final screenshots without clicking the final "Submit" button).  
2. Verify that:  
   * Known profile fields are filled via Tier 0/Tier 1 with 0 LLM tokens on the second run of the same ATS type.  
   * An intentionally unmapped screening question triggers the `[ApplyPilot HITL #ID]` email, parks the job, and closes the browser.  
   * Replying to that email updates `qa_knowledge_base`, transitions the job to `queued_resume`, and completes the form on the subsequent run without re-asking the question.

# **10\. References and Open-Source Source Repositories**

* **ApplyPilot (HITL, Gmail & Q\&A Fork):** [ibarrajo/ApplyPilot on GitHub](https://github.com/ibarrajo/ApplyPilot)  
* **ApplyPilot (Original 6-Stage Pipeline):** [Pickle-Pixel/ApplyPilot on GitHub](https://github.com/Pickle-Pixel/ApplyPilot)  
* **Official Playwright MCP Server:** [microsoft/playwright-mcp on GitHub](https://github.com/microsoft/playwright-mcp) and [Playwright MCP Documentation](https://playwright.dev/docs/getting-started-mcp)  
* **JobSpy Multi-Board Scraper:** [speedyapply/JobSpy on GitHub](https://github.com/speedyapply/JobSpy) and [JobSpy Documentation](https://github.com/cullenwatson/jobspy/blob/main/README.md)  
* **Browser Use AI Agent & MCP:** [browser-use/browser-use on GitHub](https://github.com/browser-use/browser-use) and [Browser Use MCP Guide](https://browser-use.com/posts/best-mcp-servers-to-control-a-browser)  
* **Skyvern Vision \+ Playwright Jobs Agent:** [skyvern-ai/skyvern on GitHub](https://github.com/skyvern-ai/skyvern) and [Skyvern Jobs Agent Architecture](https://www.skyvern.com/blog/launching-skyverns-jobs-agent-automate-job-applications-with-ai-2/)  
* **HumanLayer Asynchronous Email/Slack HITL:** [humanlayer/humanlayer on GitHub](https://github.com/humanlayer/humanlayer)  
* **LangGraph Human-in-the-Loop & State Interrupts:** [LangGraph Interrupts Documentation](https://docs.langchain.com/oss/python/langgraph/interrupts) and [LangGraph Interrupt Reference](https://reference.langchain.com/python/langgraph/types/interrupt)

