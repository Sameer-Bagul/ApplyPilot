# ApplyPilot End-to-End Docker Guide

This guide walks you through running ApplyPilot end-to-end inside Docker.

---

## 1. Quick Prerequisites (Arch Linux)

If Docker is not yet installed on your Arch Linux machine, run the setup script:

```bash
chmod +x docker/setup-arch.sh
./docker/setup-arch.sh
```

Or manually:
```bash
sudo pacman -S --needed docker docker-compose
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
newgrp docker   # or log out and back in
```

---

## 2. Environment Configuration

Copy the sample environment file:

```bash
cp .env.example .env
```

Edit `.env` with your preferred settings:
- `APPLYPILOT_USER_EMAIL`: Your email address for HITL questions (`Q1: A`).
- `ANTHROPIC_API_KEY`: (Optional) Fallback LLM key for non-standard forms.

---

## 3. Building the Docker Image

Build the container image with pre-installed Playwright Chromium:

```bash
docker compose build
```

---

## 4. End-to-End Workflow

### Step 1: Run First-Time Setup Wizard (Interactive)
```bash
docker compose run --rm applypilot init
```

### Step 2: Discover, Enrich & Score Jobs
Runs the discovery scrapers (JobSpy, Greenhouse, Lever, Ashby, Workday) and generates tailored resumes:
```bash
docker compose run --rm applypilot run
```

### Step 3: Check Pipeline Status
```bash
docker compose run --rm applypilot status
```

### Step 4: Run Dry-Run Auto-Apply (0 Token Verification)
```bash
docker compose run --rm applypilot apply --dry-run
```

---

## 5. Running Continuous Autonomous Services in the Background

You can run the entire autonomous pipeline with background daemons:

```bash
# Start all background services (worker pool, HITL tracker, web dashboard)
docker compose up -d worker tracker dashboard
```

Services running in background:
- **`worker`**: Autonomous parallel apply worker pool (Playwright headless Chromium).
- **`tracker`**: Continuous Gmail poller checking for HITL replies every 60 seconds (`Q1: A`).
- **`dashboard`**: Live HTML Dashboard served at [http://localhost:8080/dashboard.html](http://localhost:8080/dashboard.html).

### Viewing Service Logs
```bash
# Follow logs across all services
docker compose logs -f

# Follow logs for the worker only
docker compose logs -f worker

# Follow logs for the email HITL tracker only
docker compose logs -f tracker
```

### Stopping Services
```bash
docker compose down
```

---

## 6. Self-Learning Feedback Loop (`applypilot learn`)

Compile successful DOM selectors from application telemetry traces into the Tier 0 cache:

```bash
docker compose run --rm applypilot learn
```

---

## 7. Connecting MCP (FastMCP Server)

To expose ApplyPilot's 6 MCP tools to an external AI agent or client (e.g. Claude Desktop, Cursor, Antigravity):

```bash
docker compose run --rm -i applypilot mcp
```

---

## 8. Data Persistence

The Docker configuration uses named Docker volumes to protect all user data across rebuilds and restarts:
- `applypilot_home_data`: Persists the SQLite database (`applypilot.db`), logs, ATS session vault cookies, and tailored documents.
- `applypilot_gmail_creds`: Persists OAuth credentials (`~/.gmail-mcp/credentials.json`).
- Host directory mount (`./`): Automatically picks up your CV (`resume.pdf`), `profile.json`, and `search.yaml`.
