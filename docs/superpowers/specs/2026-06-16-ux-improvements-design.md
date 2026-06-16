---
name: Notification UX Improvements
description: Unified message format, richer clearance message, delivery logging, config hardening, and a no-lightning testing strategy
type: feature
---

# Notification UX Improvements Design

## Overview

The Thunder Alert Monitor's only user-facing surface is the notification it pushes to Telegram and LINE
(plus the operator's config/logs). This iteration improves that surface — a single shared message format
across both channels, a more informative "alert cleared" message, relative timestamps, per-channel
delivery logging, and config-time guards — and adds a testing strategy that lets us verify the rendered
messages **without waiting for a real lightning strike** (the CWA API only returns data during actual
lightning).

## Goals

- One message format, shared by Telegram and LINE (today they differ).
- Alert message shows a timezone label and a relative time ("約 3 分鐘前").
- "Alert cleared" message carries context: clearance time and how long the alert lasted.
- `AlertService` logs the per-channel delivery result, and those logs actually reach the LOG file.
- Config fails fast at startup on missing/empty/placeholder credentials, with a committed template.
- Verify the actual rendered messages on real devices without real lightning, plus automated regression
  tests on synthetic data.

## Non-goals (out of scope this iteration)

- Native location/map messages (LINE `location` / Telegram `sendLocation`) — separate, bigger change.
- Aggregating multiple strikes into one digest message — per-strike behavior stays.
- Radar-image improvements (legibility, strike marker).
- The pre-existing `get_google_url(longitude, latitude)` coordinate-order question — left unchanged so
  this iteration introduces no behavior change there.

## Components

### 1. `infrastructure/message_format.py` (new) — single source of message text

Pure functions, no I/O, `now` injectable for deterministic tests.

```python
def format_alert(alert: Alert, now: datetime | None = None) -> str
def format_clearance(earliest_occur_time: str | None = None, now: datetime | None = None) -> str
```

`now` defaults to `datetime.now(ZoneInfo("Asia/Taipei"))`. Times in `occur_time` are Taipei-local
(`"YYYY-MM-DD HH:MM"`), consistent with `utils.diff_time`.

**`format_alert` output (exact):**
```
⚡ 雷擊警報
時間：2024-01-01 12:00（台灣時間 · 約 3 分鐘前）
類型：Cloud-to-ground
位置：25.0, 121.5
地圖：https://www.google.com/maps?q=121.5,25.0
```
- Relative time rule (delta = now − occur_time): `< 60s` → `剛剛`; `< 3600s` → `約 N 分鐘前`; else
  `約 N 小時前`. A negative delta (clock skew / future) → `剛剛`.
- Map URL is `get_google_url(alert.longitude, alert.latitude)` — unchanged from today.

**`format_clearance` output (exact):**
```
✅ 雷擊警報解除
解除時間：13:05（台灣時間）
本次警戒約 18 分鐘（最早一筆 12:47）
```
- Line 3 (duration) is included only when `earliest_occur_time` is provided; duration = `now − earliest`,
  floored to whole minutes (minimum `1`).

### 2. `TelegramNotifier` / `LineNotifier` — use the shared formatter

Both `send(alert, ...)` build their text via `message_format.format_alert(alert)` instead of their own
f-strings. `LineNotifier._format_alert` is removed in favor of the shared function. `send_message(...)`
is unchanged (still sends an arbitrary string — used for the clearance message). No change to the HTTP /
Imgur / retry logic.

### 3. `AlertService` — clearance context + delivery logging

- Clearance branch builds its text with `format_clearance(earliest_occur_time=min(a.occur_time for a in
  prev_alerts))` instead of the literal `"⚠️ 雷擊警報解除"`. (`occur_time` strings sort chronologically.)
- Capture the `dict[str, bool]` returned by `send_all` / `send_message_all` and log it via `loguru`, e.g.
  `logger.info("delivery {} -> {}", alert.occur_time, results)`. Per-strike behavior is unchanged.

### 4. `infrastructure/config.py` — fail-fast validation + normalization

- A value is "unset" if it is `None`, empty/whitespace, or a placeholder (a `str` that, stripped, starts
  with `<` and ends with `>` — matching the `<your_...>` template values).
- Required keys (existing list) must be present **and not unset** → otherwise `ValueError` naming them.
- `IMGUR_CLIENT_ID` stays optional: if unset, it is removed from the returned dict so
  `AlertService`'s `config.get("IMGUR_CLIENT_ID")` sees it as absent (LINE then runs text-only). This
  fixes today's gap where the truthy placeholder string would construct a broken `ImgurClient`.

### 5. `config.example.yaml` (new, committed)

A template mirroring `config.yaml`'s structure for both `PROD` and `STAGE`, with `<your_...>` placeholders
and short comments. The real `config.yaml` remains gitignored. README gains a "copy config.example.yaml →
config.yaml and fill credentials" step plus brief LINE/Imgur setup notes.

### 6. `app/main.py` — `--test` mode + loguru interception

- **loguru interception:** install a stdlib-`logging` → `loguru` `InterceptHandler` at startup so the
  infrastructure layer's logs (notifier failures, retries, Imgur warnings) and the new delivery summary
  all reach the configured LOG sink. Today `infrastructure/*` uses stdlib `logging` while only `loguru`
  is wired to the file, so those logs are currently lost.
- **`--test` flag:** `./venv/bin/python app/main.py --test` (defaults to `--env STAGE` unless `--env` is
  given). Instead of `service.run()`, it calls `send_test_notifications(service)`:
  - Builds a synthetic `Alert` with a recent `occur_time` (now − 3 min, Taipei) and a clearly test-marked
    category (e.g. `"Cloud-to-ground (測試)"`).
  - Best-effort downloads a real radar image (`image_processor.download_thunder_img("crop.jpg")`); on
    failure, proceeds without an image.
  - Sends the **alert** message via `service.notifier.send_all(alert, img)` and the **clearance** message
    via `service.notifier.send_message_all(format_clearance(earliest_occur_time=alert.occur_time), img)`,
    logging both delivery dicts.
  - Net effect: a real Telegram + LINE message pair lands on your phone for visual inspection — no real
    lightning required. Defaulting to STAGE avoids spamming PROD.

## Testing Strategy (no real lightning required)

Two layers, neither of which needs a live strike.

### (A) Automated regression — synthetic data, no outbound sends
- **Synthetic CWA sample:** `tests/fixtures/sample_thunder.kml`, hand-authored to match the structure
  `cwb_client.get_thunder_data` produces and `_parse_alert` expects (`Document/Folder/Placemark/
  description` with `閃電種類:` / `時間:` / `經緯度: lat , long`). Contains several placemarks: in-area and
  out-of-area. This file doubles as living documentation of the assumed CWA format.
- **Parsing/filter test:** load the fixture with `lxml.html.fromstring` (as `get_thunder_data` does), call
  `is_alert_valid(doc, areas)` with `domain.alert_checker.diff_time` patched to a controlled value, and
  assert that only in-area, recent placemarks survive (one assertion set with recency passing, one with
  `diff_time` > 900 to confirm the recency cutoff).
- **Message snapshot tests:** assert the **exact** strings from `format_alert(alert, now=<fixed>)` and
  `format_clearance(earliest_occur_time=<fixed>, now=<fixed>)`. A fixed `now` makes the relative-time and
  duration output deterministic. Any future format change must deliberately update these snapshots.
- **Config tests:** placeholder/empty required value → `ValueError`; placeholder `IMGUR_CLIENT_ID` →
  removed from the returned config (treated as unset).

### (B) Manual visual verification — real channels, synthetic input
- The `--test` mode above is the mechanism: synthetic alert → real notifiers → STAGE channel → inspect the
  Telegram/LINE rendering (format, relative time, map link, image) on a real device.

The two layers use different entry points on purpose: the KML fixture exercises parsing/filtering; the
`--test` path exercises formatting + rendering + delivery. Together they cover the pipeline end to end
without a live strike.

## Files

- **New:** `infrastructure/message_format.py`, `config.example.yaml`, `tests/fixtures/sample_thunder.kml`,
  `tests/unit/test_message_format.py`, `tests/unit/test_alert_checker.py` (fixture parsing), plus config
  test additions.
- **Modified:** `infrastructure/telegram_notifier.py`, `infrastructure/line_notifier.py`,
  `services/alert_service.py`, `infrastructure/config.py`, `app/main.py`, `README.md`, and the
  notifier/alert-service tests that assert message text.

## Notes

- `--test` clearly marks its messages as tests (category suffix) so a recipient never mistakes one for a
  real alert; it defaults to STAGE to avoid PROD.
- All tests run with `./venv/bin/python -m pytest` (the venv's bare `pytest` shim is broken).
