#!/usr/bin/env bash
set -e

DATA_DIR="/home/applypilot/data"
CONFIG_DIR="/home/applypilot/.applypilot"
APP_DIR="/home/applypilot/app"

mkdir -p "$CONFIG_DIR" "$CONFIG_DIR/logs" "$CONFIG_DIR/ats_sessions"

# Link candidate profile if provided in mounted data directory
if [ -f "$DATA_DIR/profile.json" ] && [ ! -f "$CONFIG_DIR/profile.json" ]; then
    ln -sf "$DATA_DIR/profile.json" "$CONFIG_DIR/profile.json"
fi

# Link search config if provided in mounted data directory
if [ -f "$DATA_DIR/search.yaml" ] && [ ! -f "$CONFIG_DIR/search.yaml" ]; then
    ln -sf "$DATA_DIR/search.yaml" "$CONFIG_DIR/search.yaml"
fi

# Link candidate CV / resumes into workdir
shopt -s nullglob
for f in "$DATA_DIR"/*.pdf "$DATA_DIR"/*.docx; do
    if [ -f "$f" ]; then
        ln -sf "$f" "$APP_DIR/$(basename "$f")"
    fi
done
shopt -u nullglob

# Ensure database tables and config directory exist
applypilot status >/dev/null 2>&1 || true

TARGET_PORT="${PORT:-3000}"

# If START_UI or START_DASHBOARD is enabled, launch Next.js in background
if [ "${START_UI:-false}" = "true" ] || [ "${START_DASHBOARD:-false}" = "true" ]; then
    echo "[ApplyPilot] Starting Next.js UI Dashboard in background on http://0.0.0.0:${TARGET_PORT}..."
    (
        cd "$APP_DIR/dashboard"
        if [ -d ".next" ]; then
            exec npx next start -H 0.0.0.0 -p "${TARGET_PORT}"
        else
            exec npx next dev -H 0.0.0.0 -p "${TARGET_PORT}"
        fi
    ) &
fi

# Dispatch commands
case "$1" in
    all|start)
        echo "=========================================================="
        echo "🚀 [ApplyPilot] Launching Unified Autonomous Stack"
        echo "=========================================================="
        if [ "${START_MARATHON:-true}" = "true" ]; then
            echo "[ApplyPilot] Starting background Continuous Marathon Looper (--continuous)..."
            applypilot marathon --continuous &
        fi
        if [ "${START_TRACKER:-false}" = "true" ]; then
            echo "[ApplyPilot] Starting background email tracker daemon..."
            applypilot track --poll-hitl --interval 60 &
        fi
        if [ "${START_WORKER:-false}" = "true" ]; then
            echo "[ApplyPilot] Starting background apply worker daemon..."
            applypilot apply --workers "${WORKERS:-2}" &
        fi
        echo "[ApplyPilot] Starting Next.js Dashboard & REST APIs on http://0.0.0.0:${TARGET_PORT}..."
        exec applypilot dashboard --host 0.0.0.0 --port "${TARGET_PORT}"
        ;;
    dashboard)
        shift
        exec applypilot dashboard --host 0.0.0.0 --port "${TARGET_PORT}" "$@"
        ;;
    init|run|apply|status|track|learn|mcp|qa|creds|run-daily|discover-all|harvest-vc-boards|import-fundraising-founders|import-startupmap-one|loop-companies|harvest-all-directories|marathon|match-jobs|harvest-emails|outreach|outreach-top-picks)
        exec applypilot "$@"
        ;;
    -*)
        exec applypilot "$@"
        ;;
    "")
        echo "[ApplyPilot] Defaulting to unified stack..."
        exec /usr/local/bin/docker-entrypoint.sh all
        ;;
    *)
        exec "$@"
        ;;
esac
