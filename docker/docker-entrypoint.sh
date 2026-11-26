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

# If TURSO_DATABASE_URL and TURSO_AUTH_TOKEN are provided, auto-sync data down on container boot
if [ -n "$TURSO_DATABASE_URL" ] && [ -n "$TURSO_AUTH_TOKEN" ]; then
    echo "[ApplyPilot] Connecting to Turso Cloud DB (${TURSO_DATABASE_URL})..."
    python3 -c "
import os
import libsql_experimental as libsql
turso_url = os.environ.get('TURSO_DATABASE_URL')
turso_token = os.environ.get('TURSO_AUTH_TOKEN')
db_path = os.environ.get('APPLYPILOT_DB_PATH', os.path.expanduser('~/.applypilot/applypilot.db'))
os.makedirs(os.path.dirname(db_path), exist_ok=True)
try:
    print(f'[ApplyPilot] Syncing cloud database to local replica at {db_path}...')
    conn = libsql.connect(db_path, sync_url=turso_url, auth_token=turso_token)
    conn.sync()
    count = conn.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]
    print(f'[ApplyPilot] ✓ Synced successfully! {count} jobs available locally.')
except Exception as e:
    print(f'[ApplyPilot] Warning: Could not sync from Turso cloud: {e}')
" || true
fi

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
