#!/usr/bin/env bash
# Pull-based deployer, run by a systemd user timer on the target machine.
# Fast-forwards to origin/main only when that commit's CI check runs are all
# green, then syncs the venv and restarts the service. Safe to run every few
# minutes: it exits quietly when there is nothing to do or CI is not green yet.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

git fetch --quiet origin main
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)
if [ "$LOCAL" = "$REMOTE" ]; then
    exit 0
fi

OWNER_REPO=$(git remote get-url origin | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##')
if ! python3 - "$OWNER_REPO" "$REMOTE" <<'PY'
import json
import sys
import urllib.request

owner_repo, sha = sys.argv[1], sys.argv[2]
url = f"https://api.github.com/repos/{owner_repo}/commits/{sha}/check-runs"
req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
with urllib.request.urlopen(req, timeout=30) as resp:
    runs = json.load(resp).get("check_runs", [])
if not runs:
    print(f"deploy: no CI check runs yet for {sha[:9]}")
    sys.exit(1)
bad = [r for r in runs if r["status"] != "completed" or r["conclusion"] not in ("success", "skipped")]
if bad:
    states = ", ".join(f"{r['name']}={r['conclusion'] or r['status']}" for r in bad)
    print(f"deploy: CI not green yet for {sha[:9]}: {states}")
    sys.exit(1)
PY
then
    exit 0  # not green yet — the next timer tick will retry
fi

echo "deploy: updating ${LOCAL:0:9} -> ${REMOTE:0:9}"
git merge --ff-only "$REMOTE"
if [ ! -x venv/bin/python ]; then
    python3 -m venv venv
fi
./venv/bin/python -m pip install --quiet -r requirements.txt
systemctl --user restart thunder-monitor.service
echo "deploy: done — now at $(git log --oneline -1)"
