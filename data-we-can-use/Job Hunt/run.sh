#!/bin/bash
# ==============================================================================
# Job Hunt Master Engine & Application CRM - CLI & Server Launcher
# ==============================================================================

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Ensure venv exists
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install pandas openpyxl requests pydantic rich
fi

export PYTHONPATH="$DIR"

case "$1" in
    "audit")
        echo "Running forensic data integrity audit..."
        .venv/bin/python -m engine.audit
        ;;
    "build-companies")
        echo "Rebuilding Master Companies Knowledge Base (2,056 companies)..."
        .venv/bin/python -m engine.build_master_companies
        ;;
    "build-jobs")
        echo "Consolidating and scoring active jobs..."
        .venv/bin/python -m engine.build_master_jobs
        ;;
    "build-contacts")
        echo "Building contacts and outreach strategies..."
        .venv/bin/python -m engine.build_master_contacts
        ;;
    "ingest")
        echo "Running Live Active Job Ingestion Engine..."
        .venv/bin/python -m engine.live_ingest
        ;;
    "server"|"")
        echo "Starting Job Hunt Engine CRM Dashboard on http://localhost:8080..."
        .venv/bin/python server.py
        ;;
    *)
        echo "Usage: ./run.sh [server|audit|build-companies|build-jobs|build-contacts|ingest]"
        exit 1
        ;;
esac
