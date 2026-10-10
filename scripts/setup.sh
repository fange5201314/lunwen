#!/usr/bin/env bash
set -euo pipefail
task_repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$task_repo_root"
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements.lock
task_archify_dir="${THESIS_ARCHIFY_DIR:-$task_repo_root/.tools/archify}"
task_archify_commit="7f483b61e8f68d0d5c3219d2c943c5381c8db0b1"
if [[ ! -d "$task_archify_dir/.git" ]]; then
  mkdir -p "$(dirname -- "$task_archify_dir")"
  git clone --quiet https://github.com/tt-a1i/archify.git "$task_archify_dir"
fi
if ! git -C "$task_archify_dir" cat-file -e "$task_archify_commit^{commit}"; then
  git -C "$task_archify_dir" fetch origin "$task_archify_commit"
fi
git -C "$task_archify_dir" checkout --quiet "$task_archify_commit"
node "$task_archify_dir/archify/bin/archify.mjs" doctor
THESIS_ARCHIFY_DIR="$task_archify_dir" .venv/bin/python -m unittest discover -s tests -v
