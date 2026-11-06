#!/usr/bin/env bash
set -e

# ==============================================================================
# 🚀 ApplyPilot Complete Stack Launcher (UI + Headed Browser + Live Logs)
# ==============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export PYTHONUNBUFFERED=1
export APPLYPILOT_HEADLESS=false
export DISPLAY="${DISPLAY:-:1}"
if [ -n "$WAYLAND_DISPLAY" ]; then
    export WAYLAND_DISPLAY="$WAYLAND_DISPLAY"
fi

echo "========================================================================"
echo "🚀 ApplyPilot: Complete Autonomous Stack Launcher"
echo "========================================================================"
echo "  • Dashboard UI:    http://localhost:3000"
echo "  • Headed Browser:  ACTIVE on desktop display ($DISPLAY / ${WAYLAND_DISPLAY:-X11})"
echo "  • Proofs Storage:  $HOME/.applypilot/proofs/"
echo "  • Live Logs:       Streaming directly to this console"
echo "========================================================================"

# Ensure directories exist
mkdir -p "$HOME/.applypilot/proofs/videos" \
         "$HOME/.applypilot/proofs/screenshots" \
         "$HOME/.applypilot/proofs/logs"

# Graceful cleanup on Ctrl+C or termination
cleanup() {
    echo ""
    echo "🛑 [ApplyPilot] Stopping all services..."
    kill $(jobs -p) 2>/dev/null || true
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# Optional background marathon looper (job discovery + enrichment + scoring)
if [ "${1:-}" = "--with-marathon" ] || [ "${START_MARATHON:-false}" = "true" ]; then
    echo "⚡ Starting background Continuous Marathon Looper..."
    "$SCRIPT_DIR/.venv/bin/applypilot" marathon --continuous &
fi

# Launch Next.js Dashboard UI (streams all API & Playwright apply logs live)
echo "🌐 Starting Next.js Liquid-Glass Dashboard on http://localhost:3000..."
npm run dashboard

