# Deploying (pull-based)

The target machine never exposes anything to the internet and runs no CI
runner: a systemd user timer polls `origin/main`, and deploys a new commit
only after its GitHub Actions check runs are all green.

## One-time setup on the Linux box

```bash
# 1. Let user services run without an active login session
loginctl enable-linger "$USER"

# 2. Clone to the path the units expect (~/thunder-monitor), or edit %h paths
git clone https://github.com/sychen6192/thunder-monitor.git ~/thunder-monitor
cd ~/thunder-monitor

# 3. Python env (needs python3 >= 3.11)
python3 -m venv venv
./venv/bin/python -m pip install -r requirements.txt

# 4. Secrets — config.yaml is gitignored and never touched by deploys
cp config.example.yaml config.yaml   # then fill in the PROD section

# 5. Install the units
mkdir -p ~/.config/systemd/user
cp deploy/thunder-monitor.service deploy/thunder-monitor-deploy.service \
   deploy/thunder-monitor-deploy.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now thunder-monitor.service
systemctl --user enable --now thunder-monitor-deploy.timer
```

**Remove any old cron entry** from the pre-redesign batch setup: two
instances would fight over the bot's long polling (409 Conflict) and
`state.json`.

## Day to day

- Merge/push to `main` → CI runs → the box fast-forwards within ~5 minutes.
- Bot logs: `journalctl --user -u thunder-monitor -f`
- Deploy history: `journalctl --user -u thunder-monitor-deploy`
- Deploy right now: `systemctl --user start thunder-monitor-deploy.service`
- Roll back: stop the timer (`systemctl --user stop thunder-monitor-deploy.timer`),
  then `git reset --hard <sha> && systemctl --user restart thunder-monitor.service`.
  Re-enable the timer to resume tracking `main`.

The machine's checkout must stay read-only (no local commits), or the
fast-forward merge will refuse to move and the deploy log will show it.
