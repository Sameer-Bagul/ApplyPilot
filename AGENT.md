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

## 2. Core Architectural Invariants

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

## 3. Directory Structure

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
│   │   ├── api/companies/drilldown/              # Company drawer telemetry API
│   │   ├── api/stats/, jobs/, companies/, leads/ # Real-time SQLite endpoints
│   │   └── page.tsx                              # Main dashboard & drilldown drawer
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

## 4. Verification & Testing Requirements

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
3. **Confirm Guide Synchronization**:
   Verify that any new feature or altered logic is documented in the appropriate file in `docs/guide/`.

