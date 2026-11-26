# ApplyPilot End-to-End Docker Guide

This guide walks you through running ApplyPilot end-to-end inside Docker or natively.

---

## 1. Quick Prerequisites (Arch Linux / Linux)

Docker 24+ and Docker Compose v2 are required.

```bash
# Arch Linux
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

Key environment variables:
- `DASHBOARD_PORT`: Port on host machine (default: `3000`. If port 3000 is occupied, set `DASHBOARD_PORT=3001`).
- `APPLYPILOT_USER_EMAIL`: Your primary contact email.
- `ANTHROPIC_API_KEY`: (Optional) AI fallback for custom form parsing.
- `TURSO_DATABASE_URL` / `TURSO_AUTH_TOKEN`: (Optional) For remote database synchronization.

---

## 3. Building the Docker Image

The Dockerfile builds a unified container containing Python 3.12, Node.js 22 LTS, Playwright Chromium, Tesseract OCR, and the pre-compiled Next.js Dashboard:

```bash
docker compose build
```

---

## 4. How to Run the App (Two Methods)

### Method A: The Unified Autonomous Stack (Recommended for Docker)

Runs the Next.js UI dashboard, REST APIs, and background Continuous Marathon Looper together:

```bash
# Start in background
docker compose up -d

# Or with a custom port if 3000 is occupied:
DASHBOARD_PORT=3001 docker compose up -d
```

- **Open Dashboard**: [http://localhost:3000](http://localhost:3000) (or `http://localhost:3001`)
- **View Live Logs**:
  ```bash
  docker compose logs -f app
  ```
- **Stop**:
  ```bash
  docker compose down
  ```

---

### Method B: Running Outreach & CLI Commands via Docker

You can run any ApplyPilot CLI command through the containerized `cli` service:

```bash
# Check status and pipeline counts
docker compose run --rm cli status

# Run Coordinated Dual-Attack Outreach for Top Picks (Draft mode - 0 emails sent)
docker compose run --rm cli outreach-top-picks --limit 5 --mode draft

# Targeted Outreach for a specific company
docker compose run --rm cli outreach-top-picks --company Composio --mode draft

# Discover and harvest emails from company domains
docker compose run --rm cli harvest-emails --limit 10

# Run one-off marathon run
docker compose run --rm cli marathon --once
```

---

### Method C: Running Natively on Host (Arch Linux & Hyprland)

If running natively directly on your machine (ideal for visual headed browser automation on Hyprland Workspace 11):

1. **Start the Next.js Dashboard**:
   ```bash
   cd dashboard && npm run dev -- -p 3001
   # OR:
   applypilot dashboard --port 3001
   ```
   Open: [http://localhost:3001](http://localhost:3001)

2. **Run Targeted Headed Outreach on Hyprland Workspace 11**:
   ```bash
   .venv/bin/python -m applypilot outreach-top-picks --company Composio --headed --mode draft
   ```

3. **Run Continuous Autonomous Looper**:
   ```bash
   applypilot marathon --continuous
   ```

---

## 5. Data Persistence & Sync

The container shares data with your host system:
- `${HOME}/.applypilot`: Database (`applypilot.db`), logs, company intelligence, and generated email drafts are persisted directly on the host machine.
- `applypilot_gmail_creds`: Named volume for Gmail API OAuth tokens.
- `./src` & `./dashboard`: Mounted in development for immediate hot-reload.
