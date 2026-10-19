#!/usr/bin/env bash
set -e

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$PROJECT_ROOT"

# Ensure clean state
"$PROJECT_ROOT/stop_nidar_demo.sh" || true
sleep 1

# Activate venv with python-xlib
source "$PROJECT_ROOT/venv/bin/activate"

# Run recorder and director
python3 "$PROJECT_ROOT/record_full_demo.py" "$@"
