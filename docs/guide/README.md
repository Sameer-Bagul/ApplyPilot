# ApplyPilot Developer Guide & Engineering Manual

Welcome to the definitive architecture and developer manual for ApplyPilot. This directory contains detailed guides, data flow specifications, and Mermaid diagrams explaining every facet of the autonomous job acquisition pipeline.

---

## 1. Table of Contents

| Guide Document | Focus & Highlights |
| :--- | :--- |
| **[01. System Architecture Overview](file:///home/sameer/Projects/ApplyPilot/docs/guide/01_system_architecture_overview.md)** | Three-tier execution model, local SQLite database schema, Next.js UI integration with Agent Radar DAG, and master system flowchart. |
| **[02. Data Sources & Discovery Pipeline](file:///home/sameer/Projects/ApplyPilot/docs/guide/02_data_sources_and_discovery.md)** | The 7 startup directory harvesters, 11 keyless direct ATS feeds, VC portfolio boards, and Schema.org JSON-LD parser. |
| **[03. Company Looping & Email Enrichment](file:///home/sameer/Projects/ApplyPilot/docs/guide/03_company_looping_and_email_enrichment.md)** | How we loop over companies, DuckDuckGo active web search, recruiter extraction, Google DoH MX verification, and the 8-12 email guarantee. |
| **[04. Agent Execution & Dual-Attack Model](file:///home/sameer/Projects/ApplyPilot/docs/guide/04_agent_execution_and_dual_attack.md)** | Sequential vs. parallel execution, multi-worker Chrome CDP isolation, Dual-Attack application strategy, asynchronous email HITL, and the multi-lane animated Agent Radar DAG. |
| **[05. MCP System & Tool Inventory](file:///home/sameer/Projects/ApplyPilot/docs/guide/05_mcp_system_and_tool_inventory.md)** | Complete topology of 9 MCP servers, tool invocation triggers, and the 24 native FastMCP tools catalog. |

---

## 2. Quick Command Reference

### CLI Commands (via Python / uv)
```bash
# 1. Pipeline Status & Metrics
applypilot status

# 2. Omni-Directory Ingestion (Ingest 1,000+ startups & jobs)
applypilot harvest-all-directories --limit 30

# 3. Deep Company Looper (Ensure 8-12 verified emails per company & capture new roles)
applypilot loop-companies --tier 1 --limit 50 --target-emails 8

# 4. Deep Web & Social Recruiter Enrichment (DuckDuckGo + LinkedIn)
applypilot enrich-watchlist-deep --min-emails 8

# 5. Harvest VC Talent Boards (Accel, Khosla, LSVP, GC, Thrive)
applypilot harvest-vc-boards --board all --limit 50

# 6. Parallel Auto-Apply (Run 2 concurrent Chrome workers)
applypilot apply --workers 2

# 7. Asynchronous Email HITL Sync
applypilot track --poll-hitl --interval 60

# 8. Start FastMCP Server
applypilot mcp
```

### Next.js UI Dashboard
```bash
# Development server (port 3000)
npm run dashboard

# Production build & start
npm run dashboard:build
npm run dashboard:start

# Via CLI
applypilot dashboard
```

### Docker Commands
```bash
# Full Compose Stack (Dashboard + Workers + Email Tracker + FastMCP)
docker compose up -d

# Standalone Container
docker run -p 3000:3000 -v applypilot_data:/home/applypilot/.applypilot applypilot:latest
```

---

## 3. Maintenance Policy & Standing Rules

### Rule A: The Core Logic & Guide Sync Rule
Whenever any developer or AI assistant modifies:
1. Harvesters, directory parsers, or ATS feeds
2. Looping mechanics or email synthesis logic
3. Database schemas or migrations
4. Dual-Attack routing or application workers
5. Dashboard API routes or UI components

**The developer/agent MUST update the corresponding guide document in `docs/guide/` as part of that same commit.**

### Rule B: The Logic Layer ↔ UI Layer Parity Rule
Whenever a new feature, data provider, ATS integration, email synthesizer, or filter is implemented in the Python logic layer:
1. **No Invisible Features**: The feature **must** be surfaced in the Next.js iOS liquid-glass dashboard.
2. **APIs & Data Layer**: Add corresponding endpoints in `dashboard/app/api/` and queries in `dashboard/lib/db.ts`.
3. **UI Views**: Add the relevant tab, filter, table, drill-down drawer, or DAG node in `dashboard/components/agent-radar/`.
4. **Definition of Done**: A feature is incomplete if it only exists in backend Python code without user-facing UI visibility.

See [`AGENT.md`](file:///home/sameer/Projects/ApplyPilot/AGENT.md) for full instructions and enforcement guidelines.

