# ApplyPilot — Agent Operational Manual & Engineering Rules

> **MANDATORY INSTRUCTION FOR ALL AI CODING AGENTS & HUMAN DEVELOPERS**
> Read this document completely before modifying any code in this repository.

---

## 1. The Core Logic Sync Rule (STANDING RULE)

Whenever you modify:
1. **Harvesters or Discovery Pipelines** (`src/applypilot/discovery/`, `career_resolver/`, `social_discovery/`)
2. **Looping Mechanics or Email Synthesis** (`company_deep_looper.py`, `web_and_social_recruiter_harvester.py`)
3. **Database Schemas or Migrations** (`src/applypilot/database.py`, `learning/migrations.py`)
4. **Execution Routing or Dual-Attack Logic** (`apply/`, `outreach/`, `daily_runner.py`)
5. **Next.js Dashboard UI or Database APIs** (`dashboard/`, `dashboard/lib/db.ts`, `dashboard/app/api/`)
6. **MCP Server Tools or Configurations** (`mcp_server.py`, `mcp_config.json`)

**YOU MUST UPDATE THE CORRESPONDING GUIDE DOCUMENT IN [`docs/guide/`](file:///home/sameer/Projects/ApplyPilot/docs/guide/) AS PART OF THAT SAME TASK.**

- System Architecture changes $\to$ update [`docs/guide/01_system_architecture_overview.md`](file:///home/sameer/Projects/ApplyPilot/docs/guide/01_system_architecture_overview.md)
- Data sources or harvester changes $\to$ update [`docs/guide/02_data_sources_and_discovery.md`](file:///home/sameer/Projects/ApplyPilot/docs/guide/02_data_sources_and_discovery.md)
- Looping or email synthesis changes $\to$ update [`docs/guide/03_company_looping_and_email_enrichment.md`](file:///home/sameer/Projects/ApplyPilot/docs/guide/03_company_looping_and_email_enrichment.md)
- Concurrency, workers, or Dual-Attack changes $\to$ update [`docs/guide/04_agent_execution_and_dual_attack.md`](file:///home/sameer/Projects/ApplyPilot/docs/guide/04_agent_execution_and_dual_attack.md)
- MCP server, tool, or protocol changes $\to$ update [`docs/guide/05_mcp_system_and_tool_inventory.md`](file:///home/sameer/Projects/ApplyPilot/docs/guide/05_mcp_system_and_tool_inventory.md)

Documentation must NEVER drift out of sync with the codebase.

---

## 2. The Logic Layer ↔ UI Layer Parity Rule (MANDATORY)

ApplyPilot is designed as an integrated autonomous system where the **Logic Layer** (Python engines, harvesters, deep loopers, ATS pollers, parallel workers, SQLite database) and the **UI Layer** (Next.js 16 iOS liquid-glass dashboard, telemetry streams, branching DAG radar, company drill-down drawer) operate in complete lockstep.

**WHENEVER YOU INTRODUCE OR MODIFY A FEATURE IN THE LOGIC LAYER, YOU MUST UPDATE THE UI LAYER IN THE SAME TASK:**

1. **No Invisible Backend Features**:
   - If a new harvester, data provider, ATS integration, looper strategy, email synthesizer, or search filter is built in Python, it **must** be surfaced in the dashboard.
   - The user must never be forced to inspect the database via raw SQLite CLI to see what the system is doing.
2. **Dashboard Data Layer & APIs (`dashboard/lib/db.ts`, `dashboard/app/api/`)**:
   - Expose the newly generated data, tables, columns, or metrics through clean, typed API routes.
   - Use built-in `node:sqlite` for synchronous, zero-dependency reads from `~/.applypilot/applypilot.db`.
3. **User Interface Controls & Views (`dashboard/app/page.tsx`, `dashboard/components/`)**:
   - Provide corresponding cards, filters, tables, or interactive drill-downs.
   - Maintain the strict iOS liquid-glass design language: frosted glass (`backdrop-blur-xl`), soft ambient mesh glows, radial peach orb accents, and **strictly zero emojis** (Lucide React icons only).
4. **Agent Radar & DAG Synchronization (`dashboard/components/agent-radar/`)**:
   - If the feature introduces a new execution phase, autonomous subagent, or telemetry trace, update the multi-lane branching DAG, scenario steps, and `/api/agent-pipeline/telemetry` so the visualizer reflects the runtime reality.
5. **Definition of Done**:
   - A feature is **INCOMPLETE** if it only exists in backend Python code. A task is concluded only when both the logic layer AND the UI layer are fully implemented, functional, and verified together.

---

## 3. Core Architectural Invariants

1. **Zero Emojis Everywhere**:
   - The UI and console output MUST strictly avoid emojis. Use only clean vector icons (Lucide React) in the web UI and clean text indicators in console logging.
2. **Light Theme iOS Liquid-Glass UI**:
   - The Next.js dashboard must adhere to the frosted glass, soft ambient glow, radial peach orb, and spacious human-centered design principles inspired by iOS liquid glass.
   - No unnecessary badge clutter, container nesting, or AI slop.
3. **Guaranteed 8-12 Verified Emails Per Company**:
   - Every company in `career_watchlist` must reach at least 8 to 12 verified emails.
   - Obtained via DuckDuckGo active recruiter search, founder name permutations, Google DoH MX verification, and standard corporate recruitment aliases.
4. **Dual-Attack Default**:
   - Discovered jobs for companies with verified recruiter emails must be routed as `DUAL_ATTACK` (submitting official ATS portal application while concurrently sending cold recruiter outreach citing the application).
5. **Node.js Native SQLite**:
   - The Next.js dashboard data layer (`dashboard/lib/db.ts`) uses built-in `node:sqlite` for synchronous, zero-dependency reads from `~/.applypilot/applypilot.db`.

---

## 4. Directory Structure

```
ApplyPilot/
├── AGENT.md                                      # This manual & standing rules
├── mcp_config.json                               # 9-server multi-MCP configuration
├── docs/
│   └── guide/                                    # Developer & architecture guides
│       ├── README.md                             # Index & quick command sheet
│       ├── 01_system_architecture_overview.md    # 3-tier model & SQLite schema
│       ├── 02_data_sources_and_discovery.md      # 7 directories & 11 ATS feeds
│       ├── 03_company_looping_and_email_enrichment.md # DuckDuckGo search & MX verify
│       ├── 04_agent_execution_and_dual_attack.md # Worker pool & Dual-Attack model
│       └── 05_mcp_system_and_tool_inventory.md   # Topology of 9 MCP servers & 24 tools
├── dashboard/                                    # Next.js 16 iOS Liquid-Glass UI
│   ├── app/                                      # App Router, pages, & API routes
│   │   ├── api/agent-pipeline/                   # DAG scenarios & live telemetry
│   │   ├── api/companies/drilldown/              # Company drawer telemetry API
│   │   ├── api/stats/, jobs/, companies/, leads/ # Real-time SQLite endpoints
│   │   └── page.tsx                              # Main dashboard & drilldown drawer
│   ├── components/agent-radar/                   # Multi-lane DAG, ScrambleText, Inspector
│   └── lib/db.ts                                 # Native node:sqlite data layer
├── src/applypilot/
│   ├── apply/                                    # Multi-worker Chrome CDP engine
│   ├── discovery/                                # Harvesters, looper, social dorker
│   │   ├── company_deep_looper.py                # Deep company sweep engine
│   │   ├── web_and_social_recruiter_harvester.py # DDG recruiter search & inboxes
│   │   ├── multi_directory_orchestrator.py       # Omni-channel coordinator
│   │   └── ats_direct_feeds.py                   # 11 keyless ATS endpoints
│   ├── hitl/                                     # Asynchronous email reply tracker
│   ├── outreach/                                 # Cold recruiter email composer
│   ├── learning/                                 # Tier 0 cache & schema migrations
│   ├── cli.py                                    # Typer CLI application
│   └── mcp_server.py                             # FastMCP server (24 native tools)
└── tests/                                        # Pytest suite
```

---

## 5. Verification & Testing Requirements

Before concluding any development task:
1. **Run Python Pytest Suite**:
   ```bash
   .venv/bin/pytest tests/test_next_level_harvesters_and_looper.py tests/test_web_and_social_recruiter_harvester.py
   ```
   All tests must pass with 0 failures.
2. **Verify Next.js Dashboard Build**:
   ```bash
   cd dashboard && npm run build
   ```
   Must compile with 0 TypeScript errors and 0 build failures.
3. **Verify Logic ↔ UI Parity**:
   Confirm that all new backend features, entities, or metrics are visible, filterable, or actionable in the Next.js UI dashboard.
4. **Confirm Guide Synchronization**:
   Verify that any new feature or altered logic is documented in the appropriate file in `docs/guide/`.

