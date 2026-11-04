#!/usr/bin/env bash
set -e

# ApplyPilot Unified Launcher
# Starts Next.js UI Dashboard + REST APIs + Background Autonomous Looper

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "=========================================================="
echo "🚀 ApplyPilot — Unified System Launcher"
echo "=========================================================="

# Check if Docker is available
if command -v docker >/dev/null 2>&1; then
    echo "[ApplyPilot] Launching full stack via Docker..."
    docker compose up -d
    echo ""
    echo "✅ ApplyPilot is now running in the background!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 Dashboard UI & APIs:  http://localhost:3000"
    echo "📜 Live Engine Logs:     docker compose logs -f"
    echo "🛑 Stop System:          docker compose down"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    echo "[ApplyPilot] Docker not found, launching natively..."
    echo "[1/2] Starting Next.js Dashboard on http://localhost:3000..."
    (
        cd "$ROOT_DIR/dashboard"
        if [ -d ".next" ]; then
            exec npx next start -p 3000
        else
            exec npx next dev -p 3000
        fi
    ) &

    echo "[2/2] Starting Continuous Marathon Looper..."
    source "$ROOT_DIR/.venv/bin/activate"
    exec applypilot marathon --continuous
fi
