# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Thunder Alert Monitor is a Python 3.11 batch job that fetches real-time lightning-strike data from Taiwan's Central Weather Administration (CWA) OpenData, filters strikes by geographic area and recency, and pushes alerts (with a cropped radar image) to messaging channels (Telegram, plus optional LINE). It runs as a one-shot process (cron / AWS Lambda-style), not a long-running server.

## Commands

The `venv/` was created at a previous path (`/Users/sychen/thunder-monitor`), so its entry-point scripts have a broken shebang — **`pytest`/`pip` console scripts and `source venv/bin/activate` fail with `bad interpreter`.** Always invoke the interpreter binary directly (that file is fine):

- Run all tests: `./venv/bin/python -m pytest`
- Single test: `./venv/bin/python -m pytest "tests/unit/test_file_repo.py::TestFileRepo::test_round_trip_save_and_load"`
- Run the app: `./venv/bin/python app/main.py --env STAGE` (`--env` is `PROD` (default) or `STAGE`)
- Send synthetic test notifications (no real lightning needed; defaults to STAGE): `./venv/bin/python app/main.py --test`
- Install/update deps: `./venv/bin/python -m pip install -r requirements.txt`

System `python3` is 3.14 and lacks the project deps; only `venv` (3.11) has them. There are no `__init__.py` files and no pytest config file — `python -m pytest` works because `-m` puts the repo root on `sys.path`, making `models`, `infrastructure`, `domain`, `services` importable as top-level packages (bare `pytest` would not). **Run everything from the repo root**: `config.yaml`, `alert.txt`, `crop.jpg`, and `log/` are all hardcoded relative to CWD. VS Code uses Pyright `basic` type-checking; the code is fully type-hinted.

## Architecture

Layered / clean-architecture with a one-directional dependency flow `app → services → domain → models`, where `infrastructure` provides I/O adapters and `domain` stays pure (no I/O).

- `app/main.py` — entry point: parse `--env`/`--test`, configure `loguru` file logging (an `InterceptHandler` bridges stdlib `logging` from infrastructure modules into the loguru sink), build and run `AlertService`.
- `services/alert_service.py` — `AlertService.run()` orchestrates the whole job and is the heart of the system:
  1. `file_repo.load_alerts()` — previous run's alerts (deduplication state)
  2. `cwb_client.get_thunder_data()` — fetch + parse CWA data
  3. `is_alert_valid()` — keep only valid, in-area, recent strikes
  4. diff against previous → `new_alerts`
  5. if new alerts: download radar crop, then `NotificationManager.send_message_all(format_alert(alert), "crop.jpg")` per alert, and persist current alerts
  6. if previously-active alerts have all cleared: reset state and broadcast a `format_clearance(...)` "警報解除" (alert-cleared) message
- `domain/alert_checker.py` — pure logic: parses each KML `<description>` (Chinese-language regex `閃電種類`/`時間`/`經緯度`), keeps strikes within 900s (15 min) and inside configured areas.
- `infrastructure/` — adapters:
  - `cwb_client` (CWA `O-A0039-001` KMZ → unzip → KML → lxml)
  - `image_processor` (crops a fixed pixel box from CWA's radar JPG and stamps a timestamp)
  - `file_repo` (JSONL dedup store in `alert.txt`; skips malformed lines on load so a crash-truncated file can't wedge every later run)
  - `config` (loads + validates `config.yaml`)
  - `message_format` (`format_alert` / `format_clearance` — the single source of message text, with Taipei-tz relative times)
  - `utils` (Google Maps URL + Taipei-tz time diff)
  - `notifier` (the `Notifier` ABC), `telegram_notifier`, `line_notifier`, `imgur_client`, `notification_manager`
- `models/alert.py` — `Alert` dataclass with `to_dict()`/`from_dict()` for JSONL serialization.

### Notification system
`AlertService → NotificationManager → [TelegramNotifier, LineNotifier]`.

- The `Notifier` ABC exposes a single method: `send_message(message: str, img_path: str | None = None) -> bool` (True on success, False on failure). Alerts are turned into text by `message_format.format_alert()` at the call site, so notifiers only handle ready-to-send strings.
- `NotificationManager.send_message_all()` fans a message out to every notifier, isolates per-channel failures, retries each up to `max_retries` (default 1) extra times, and returns `{ClassName: ok}`.
- `LineNotifier` requires HTTPS image URLs, so it uploads `crop.jpg` via `ImgurClient` and falls back to text-only if Imgur is unavailable. LINE is optional: blank both LINE keys in `config.yaml` for a Telegram-only setup; omit `IMGUR_CLIENT_ID` for LINE text-only.

### Data sources
- Lightning: CWA OpenData fileapi `O-A0039-001`, downloaded as KMZ; requires `CWB_TOKEN`.
- Radar image: CWA `lightning_s.jpg`, cropped to a hardcoded pixel box in `image_processor.py`.

### Coordinate convention (easy to get wrong)
`_parse_alert` splits the `經緯度` string `"a , b"` into `Alert(latitude=a, longitude=b)`. `domain/alert_checker.py:_in_areas` treats each `AREAS` entry as `[top, down, left, right]` and tests `left <= latitude <= right and down <= longitude <= top` — i.e. the field named `latitude` is bounded by `left`/`right`. Verify axis ordering against a real CWA payload before changing the area filter or `AREAS` config.

## Configuration

`config.yaml` has top-level environment keys (`PROD`, `STAGE`); `load_config(env)` returns that sub-dict and validates it — it fails fast on missing or blank/`<placeholder>` values, and drops any unset optional keys. Copy `config.example.yaml` to `config.yaml` to start.

- **Required** per env: `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`, `CWB_TOKEN`, `LOG`, `AREAS` (list of `[top, down, left, right]` boxes).
- **Optional**: `LINE_CHANNEL_ACCESS_TOKEN` + `LINE_TO` (blank both → Telegram-only), `IMGUR_CLIENT_ID` (omit → LINE text-only).
- `DEBUG` also appears in the YAML (loaded but not validated/required). `STAGE` uses a single small test area and a separate log file (`./log/thunder_stage.log`).

`config.yaml` is **gitignored** — keep real tokens out of version control; never commit secrets.

## Conventions

This repo follows a "superpowers" spec→plan→implement workflow with a TDD-style, per-task commit cadence (visible in git history). Design specs and task plans live under `docs/superpowers/`. Progress was tracked via commits rather than by editing the plans, so their `- [ ]` checkboxes may read as unchecked even where the work has landed — trust the code and git history over the checkboxes.
