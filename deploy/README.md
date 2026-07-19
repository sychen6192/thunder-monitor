# Deploying (Docker + GHCR + watchtower)

Push/merge to `main` → the `Deploy` workflow runs tests on GitHub-hosted
runners, then builds and pushes `ghcr.io/sychen6192/thunder-monitor`
(`:latest` + `:<sha>`). On the box, watchtower polls the registry every
5 minutes and restarts the container on a new image. The box holds no
GitHub credentials and exposes nothing inbound.

## One-time setup on the box

```bash
mkdir -p ~/thunder-monitor-deploy/data
cp deploy/compose.yaml ~/thunder-monitor-deploy/compose.yaml
# Secrets: put a filled-in config.yaml at ~/thunder-monitor-deploy/data/config.yaml
# (copy config.example.yaml as the template; deploys never touch /data)
cd ~/thunder-monitor-deploy
docker compose up -d
```

**Remove any old cron entry** from the pre-redesign batch setup: two
instances would fight over the bot's long polling (409 Conflict) and state.

The GHCR package must be **public** for anonymous pulls (repo → Packages →
thunder-monitor → settings → visibility), or run `docker login ghcr.io`
once with a `read:packages` token instead.

## Day to day

- Merge/push `main` → green tests → image published → box updates within ~5 min.
- Bot logs: `docker compose logs -f thunder-monitor` (file log also in `data/log/`).
- State/radar/config all live in `~/thunder-monitor-deploy/data/`.
- Deploy right now: `docker compose pull && docker compose up -d`.
- Roll back: stop watchtower (`docker compose stop watchtower`), pin the
  image to a `:<sha>` tag in compose.yaml, `docker compose up -d`; revert
  and restart watchtower to resume tracking `latest`.
