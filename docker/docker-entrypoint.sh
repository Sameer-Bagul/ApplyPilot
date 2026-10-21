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

# Dispatch commands
case "$1" in
    init|run|apply|status|track|learn|mcp|qa|creds)
        exec applypilot "$@"
        ;;
    dashboard)
        shift
        exec applypilot dashboard --serve --host 0.0.0.0 --port 8080 "$@"
        ;;
    -*)
        exec applypilot "$@"
        ;;
    "")
        exec applypilot --help
        ;;
    *)
        exec "$@"
        ;;
esac
