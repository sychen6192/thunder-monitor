#!/usr/bin/env bash
# Deploys the app checkout this script lives in (normally ~/thunder-monitor).
#
# Two modes:
#   - From GitHub Actions (DEPLOY_SHA set): the workflow's `needs: test` gate
#     already vouches for the commit — fast-forward to exactly that SHA.
#   - Manual (no DEPLOY_SHA): fast-forward to origin/main only when its
#     "test*" check runs are all green (public API, no auth needed).
#     Pass --force to skip the CI check.
set -euo pipefail

# The Actions runner service has no user-session environment; point systemctl
# --user at this user's manager explicitly (requires loginctl enable-linger).
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=${XDG_RUNTIME_DIR}/bus}"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

git fetch --quiet origin main
LOCAL=$(git rev-parse HEAD)
TARGET="${DEPLOY_SHA:-}"

if [ -z "$TARGET" ]; then
    TARGET=$(git rev-parse origin/main)
    if [ "$LOCAL" = "$TARGET" ]; then
        exit 0
    fi
    if [ "${1:-}" != "--force" ] && ! python3 - "$(git remote get-url origin | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##')" "$TARGET" <<'PY'
import json
import sys
import urllib.request

owner_repo, sha = sys.argv[1], sys.argv[2]
url = f"https://api.github.com/repos/{owner_repo}/commits/{sha}/check-runs"
req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
with urllib.request.urlopen(req, timeout=30) as resp:
    runs = [r for r in json.load(resp).get("check_runs", []) if r["name"].startswith("test")]
if not runs:
    print(f"deploy: no test check runs yet for {sha[:9]}")
    sys.exit(1)
bad = [r for r in runs if r["status"] != "completed" or r["conclusion"] not in ("success", "skipped")]
if bad:
    states = ", ".join(f"{r['name']}={r['conclusion'] or r['status']}" for r in bad)
    print(f"deploy: CI not green yet for {sha[:9]}: {states}")
    sys.exit(1)
PY
    then
        exit 0  # not green yet — retry later or use --force
    fi
fi

if [ "$LOCAL" = "$TARGET" ]; then
    echo "deploy: already at ${TARGET:0:9}"
    exit 0
fi

echo "deploy: updating ${LOCAL:0:9} -> ${TARGET:0:9}"
git fetch --quiet origin "$TARGET"
git merge --ff-only "$TARGET"
if [ ! -x venv/bin/python ]; then
    python3 -m venv venv
fi
./venv/bin/python -m pip install --quiet -r requirements.txt
# try-restart: restarts only if the service is already running, so deploys
# stay green during staged bring-up before `systemctl --user enable --now`.
systemctl --user try-restart thunder-monitor.service
echo "deploy: done — now at $(git log --oneline -1)"
