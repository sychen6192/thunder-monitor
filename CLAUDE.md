# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Thunder Alert Monitor is a Python 3.11+ **long-running Telegram bot** that fetches real-time lightning-strike data from Taiwan's Central Weather Administration (CWA) OpenData, filters strikes by geographic area and recency, and pushes **one digest notification per detection round** (photo + HTML caption + inline buttons). It also serves interactive commands (`/status`, `/radar`, `/recent`, `/mute`, `/unmute`, `/test`, `/help`). A `--once` mode runs a single detection round without the bot for cron/Lambda-style deployments.

## Commands

Create the venv fresh if it's missing (`python3 -m venv venv && ./venv/bin/pip install -r requirements.txt`). Invoke the interpreter binary directly and **run everything from the repo root** — `config.yaml`, `state.json`, `crop.jpg` and `log/` are CWD-relative:

- Run all tests: `./venv/bin/python -m pytest`
- Single test: `./venv/bin/python -m pytest "tests/unit/test_monitor.py::test_new_alerts_send_single_digest_and_persist"`
- Run the daemon: `./venv/bin/python app/main.py --env PROD` (`--env` is `PROD` (default) or `STAGE`)
- Single detection round, no bot (cron-compatible): `./venv/bin/python app/main.py --once`
- Send synthetic test notifications (no real lightning needed; defaults to STAGE): `./venv/bin/python app/main.py --test`

There are no `__init__.py` files and no packaging — `python -m pytest` puts the repo root on `sys.path` (making `models`, `infrastructure`, `domain`, `services` top-level), and `app/main.py` bootstraps `sys.path` itself so `python app/main.py` works directly. `pytest.ini` sets `asyncio_mode = auto`, so async test functions need no decorator. VS Code uses Pyright `basic` type-checking; the code is fully type-hinted.

## Architecture

Layered, one-directional dependency flow `app → services → domain → models`, with `infrastructure` providing I/O adapters and `domain` staying pure. The process is a python-telegram-bot (PTB v22) `Application`: a JobQueue fires a detection round every `POLL_INTERVAL_SECONDS`, and command handlers serve the authorized chat/users (`command_filter`). A single shared `asyncio.Lock` serializes all `state.json` writes (detection rounds and `/mute`/`/unmute`).

- `app/main.py` — entry point: parse `--env`/`--once`/`--test`, configure `loguru` file logging (an `InterceptHandler` bridges stdlib `logging` into the loguru sink), build the PTB `Application`, register `CommandHandler`s behind `command_filter` — the push chat, plus any `COMMAND_USER_IDS` from any chat — start JobQueue + polling. A `MessageHandler` in group 1 logs every unauthorized update and answers a *command* from a stranger with one `unauthorized_text` denial per chat per `UNAUTHORIZED_REPLY_COOLDOWN` (non-command messages stay silent, so the bot never becomes an echo for whoever finds the username).
- `services/monitor.py` — `Monitor.run_once()` is one detection round, the heart of the system:
  1. `state_repo.load_state()` — previous state (dedup, episode, mute)
  2. `cwb_client.get_thunder_data()` (via `asyncio.to_thread`) → `is_alert_valid()` filter
  3. diff against `state.active_alerts` → `new_alerts`
  4. new strikes → update episode + history, then **one** `format_digest` message (radar photo, map/CWA buttons; radar failure degrades to text-only)
  5. previously-active alerts all gone → `format_all_clear` (episode duration + count), reset episode
  6. persist state with a `LastCheck` record; return `CheckResult`
  Mute skips sends but **still records** state; no catch-up messages after unmute.
- `services/bot_commands.py` — thin async handlers; reply text comes from `message_format` pure functions. `/mute` takes the shared lock; `/test` pushes a synthetic strike (first area's center, category marked 測試) through the real digest pipeline, delivered to the chat that asked (CLI `--test`, which passes no update, goes to the push chat). All replies use `update.effective_message`, so a command run from a DM answers in that DM while alerts still go only to `TELEGRAM_CHAT_ID`.
- `domain/alert_checker.py` — pure logic: parses KML `<description>` (`閃電種類`/`時間`/`經緯度`), keeps strikes within 900s and inside configured areas; `area_name_of()` resolves a point to its area name.
- `infrastructure/` — adapters:
  - `cwb_client` (CWA `O-A0039-001` KMZ → unzip → KML → lxml); the shared `cwa_http.fetch_bytes` retries transient fetch failures (timeout/5xx/TLS) a few times with linear backoff before giving up, so a single CWA blip doesn't fail the round
  - `healthcheck` (best-effort healthchecks.io ping after each round: base URL on success; `/fail` only once a round has failed `HEALTHCHECK_FAIL_THRESHOLD` times **in a row** — a sub-threshold failure pings nothing and lets the missed heartbeat lapse into the grace period, so one transient blip never pages; empty URL disables; all errors swallowed so a ping never breaks a round)
  - `radar` (downloads CWA's radar JPG, crops `CROP_BOX`, 2x LANCZOS upscale, stroke-outlined Taipei timestamp)
  - `state_repo` (`state.json`: active alerts, `muted_until`, `last_check`, 24h/200-entry history, episode fields, `consecutive_failures` counter; corrupt/partial files reset to empty state instead of wedging later runs)
  - `config` (loads + validates `config.yaml`; normalizes `AREAS` to `{name, box}`; `POLL_INTERVAL_SECONDS` defaults to 60)
  - `message_format` (single source of user-facing text: digest/single/all-clear notifications in Telegram-HTML with escaped dynamic fields, plus `status_text`/`recent_text`/help/mute texts; `now` injectable for snapshot tests)
  - `telegram` (`TelegramSender`: async photo+caption/text sends with inline URL buttons, per-send retry, photo→text degradation)
  - `utils` (Google Maps URL + Taipei-tz time diff)
- `models/alert.py` — `Alert` dataclass with `to_dict()`/`from_dict()`.

### Coordinate convention

CWA's `經緯度` field is **longitude-first** (`"120.2 , 22.6"`); `_parse_alert` assigns fields by real meaning (`latitude=22.6`, `longitude=120.2`). `AREAS` boxes are `[top, down, left, right]` = `[lat N, lat S, long W, long E]`, checked as `down <= lat <= top and left <= long <= right`. Display order is always standard `(lat, long)`; `get_google_url(lat, long)`. (A historical double-swap bug here was fixed in the telegram-bot redesign — see `docs/superpowers/specs/2026-07-18-telegram-bot-redesign.md`.)

## Configuration

`config.yaml` has top-level environment keys (`PROD`, `STAGE`); `load_config(env)` returns that sub-dict and fails fast on missing/blank/`<placeholder>` values. Copy `config.example.yaml` to start.

- **Required** per env: `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` (alert push target; commands are always allowed from this chat), `CWB_TOKEN`, `LOG`, `AREAS`.
- **Optional**: `POLL_INTERVAL_SECONDS` (default 60); `HEALTHCHECK_URL` (healthchecks.io dead-man's-switch, blank/absent/placeholder → disabled); `HEALTHCHECK_FAIL_THRESHOLD` (consecutive failed rounds before a `/fail` ping, default 3, floored at 1); `COMMAND_USER_IDS` (numeric user ids allowed to run commands from *any* chat, e.g. a DM; absent → `[]`, i.e. push-chat-only). `DEBUG` is loaded but not validated.
- `AREAS` entries: `{name: 高雄, box: [top, down, left, right]}`; legacy bare boxes still parse and get `區域 N` names.
- Legacy `LINE_*`/`IMGUR_*` keys in an old `config.yaml` are ignored.
- `config.yaml` is **gitignored** — never commit secrets. `state.json`/`crop.jpg` are runtime artifacts, also gitignored.

## Conventions

This repo follows a "superpowers" spec→plan→implement workflow with a TDD-style, per-task commit cadence (visible in git history). Design specs live under `docs/superpowers/`. Progress is tracked via commits rather than by editing the specs — trust the code and git history over any unchecked checkboxes. Message strings are locked by exact snapshot tests in `tests/unit/test_message_format.py`; changing wording means deliberately updating those snapshots.
