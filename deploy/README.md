# Deploying (self-hosted runner)

Push to `main` → `Deploy` workflow: tests run on GitHub-hosted runners, and
only after they pass does the `deploy` job run on the self-hosted runner,
which fast-forwards `~/thunder-monitor`, syncs the venv, and restarts the
bot service. `config.yaml` and `state.json` are untracked, so deploys never
touch them.

## One-time setup on the Linux box

```bash
# 1. Let user services run without an active login session
loginctl enable-linger "$USER"

# 2. App checkout at the path the units and workflow expect
git clone https://github.com/sychen6192/thunder-monitor.git ~/thunder-monitor
cd ~/thunder-monitor

# 3. Python env (needs python3 >= 3.11)
python3 -m venv venv
./venv/bin/python -m pip install -r requirements.txt

# 4. Secrets — config.yaml is gitignored and never touched by deploys
cp config.example.yaml config.yaml   # then fill in the PROD section

# 5. Bot service
mkdir -p ~/.config/systemd/user
cp deploy/thunder-monitor.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now thunder-monitor.service
```

**Remove any old cron entry** from the pre-redesign batch setup: two
instances would fight over the bot's long polling (409 Conflict) and
`state.json`.

## Runner install

Repo → Settings → Actions → Runners → **New self-hosted runner** (Linux x64)
and paste the commands it shows (download, `./config.sh --url ... --token ...`).
Then install it as a service so it survives reboots:

```bash
cd ~/actions-runner
sudo ./svc.sh install "$USER"
sudo ./svc.sh start
```

## Public-repo safety rails (do not loosen)

- `deploy.yml` triggers only on `push` to `main` and `workflow_dispatch` —
  **never add `pull_request` to it**; fork PRs must not reach the runner.
- PR tests stay on GitHub-hosted runners (`ci.yml`).
- Settings → Actions → General: require approval for **all** outside
  collaborators' workflow runs; keep the workflow token read-only.
- The runner is registered to this single repo, not the whole account.

## Day to day

- Merge/push `main` → green tests → the box updates within a minute or two.
- Use a merge commit (not squash) when merging PRs: the box fast-forwards,
  and a squashed history would refuse to fast-forward until a manual reset.
- Bot logs: `journalctl --user -u thunder-monitor -f`
- Deploy logs: the `Deploy` run's `deploy` job in the Actions tab.
- Manual deploy from the box: `deploy/deploy.sh` (gates on green CI; `--force` skips).
- Roll back: `git reset --hard <sha> && systemctl --user restart thunder-monitor.service`
  on the box (the next main deploy will move it forward again).
