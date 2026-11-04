#!/usr/bin/env bash
set -e

# ApplyPilot Unified Launcher
# Starts Next.js UI Dashboard + REST APIs + Background Continuous Looper

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
    echo "✅ ApplyPilot is actively running!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 Dashboard UI & APIs:  http://localhost:3000"
    echo "📜 Live Engine Logs:     docker compose logs -f app"
    echo "🛑 Stop Stack:           docker compose down"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    # If --daemon or -d is passed, exit quietly. Otherwise, attach live log stream.
    if [ "$1" = "--daemon" ] || [ "$1" = "-d" ]; then
        echo "[ApplyPilot] Running in background mode (-d). Exiting launcher."
        exit 0
    else
        echo "[ApplyPilot] Attaching to live continuous marathon stream..."
        echo "(Press Ctrl+C at any time to detach; the engine will keep running in the background)"
        echo ""
        exec docker compose logs -f --tail=30 app
    fi
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
