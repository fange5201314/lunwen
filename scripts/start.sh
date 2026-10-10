#!/usr/bin/env bash
set -euo pipefail
task_repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$task_repo_root"
export THESIS_ARCHIFY_DIR="${THESIS_ARCHIFY_DIR:-$task_repo_root/.tools/archify}"
# PoC has one local state owner. Remote laptop transport/auth is a later stage.
exec .venv/bin/python -m uvicorn workstation.main:app --host 127.0.0.1 --port 8765 --workers 1
