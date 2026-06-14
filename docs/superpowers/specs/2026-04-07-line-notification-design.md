---
name: Line Notification Integration
description: Design for adding LINE Messaging API notifications with Imgur-hosted radar images
type: feature
---

# LINE Notification Integration Design

> **Revised 2026-06-14** (supersedes the original 2026-04-07 draft): use raw `requests` instead of
> `line-bot-sdk`/`pyimgur` (remove those deps); drop `LINE_CHANNEL_SECRET` (push-only, no webhook);
> Imgur is the image host (text-only fallback if it fails); per-strike sending retained.

## Overview

Add LINE Messaging API notifications alongside the existing Telegram notifications, so each lightning
alert — and the "alert cleared" message — is pushed to both channels. A Strategy pattern (a `Notifier`
interface plus a `NotificationManager`) makes channels pluggable and independently testable. LINE only
accepts images as HTTPS URLs, so the cropped radar image is hosted on Imgur and sent as a URL.

## Goals / Non-goals

**Goals**
- Deliver every alert and clearance message to both Telegram and LINE.
- Include the cropped radar image in LINE messages (via Imgur).
- A failure in one channel must not block the other.
- Preserve the current per-strike sending behavior.

**Non-goals (YAGNI)**
- No webhook receiver or reply handling — push only.
- No message batching or rate-limit throttling this iteration (see Known Limitations).
- No async/parallel delivery — sequential is fine at this volume.
- No additional channels (email/SMS/Discord) — the interface leaves room, but they are not built now.

## Architecture

```
AlertService → NotificationManager → ┌ TelegramNotifier
                                      └ LineNotifier → ImgurClient
```

## Components

### `Notifier` — `infrastructure/notifier.py` (exists)
Abstract base. `send(alert, img_path=None) -> bool` and `send_message(message, img_path=None) -> bool`.
Contract: return `True` on success, `False` on a handled delivery failure; do not raise for normal
failures (network, API error).

### `TelegramNotifier` — `infrastructure/telegram_notifier.py` (modify)
- Inherit `Notifier`.
- Wrap the existing `requests.post` calls in try/except, return `bool`, log on failure. (Today it can
  raise and abort the whole run.)
- Behavior otherwise unchanged.

### `LineNotifier` — `infrastructure/line_notifier.py` (new)
- Implements `Notifier`, raw `requests`.
- `__init__(channel_access_token, to, imgur_client=None)`.
- Push: `POST https://api.line.me/v2/bot/message/push`, header `Authorization: Bearer <token>`,
  body `{"to": <to>, "messages": [...]}`.
- Always sends a text message (alert formatted, including the Google Maps link). When `img_path` and
  `imgur_client` are both present: upload via Imgur → on success append an image message
  (`originalContentUrl`/`previewImageUrl` = Imgur URL); on failure send text-only and log a warning.
- Returns `True`/`False` from the LINE API response.

### `ImgurClient` — `infrastructure/imgur_client.py` (new)
- Raw `requests`. `__init__(client_id)`, `upload_image(path) -> str | None`.
- `POST https://api.imgur.com/3/image`, header `Authorization: Client-ID <client_id>`.
- Returns `data.link` (HTTPS) on success, `None` on any failure (logged).

### `NotificationManager` — `infrastructure/notification_manager.py` (new)
- `__init__(notifiers: list[Notifier], max_retries=1)`.
- `send_all(alert, img_path=None) -> dict[str, bool]`: for each notifier, try up to `max_retries + 1`
  times, catch exceptions, record success keyed by class name. One notifier failing never stops others.
- `send_message_all(message, img_path=None) -> dict[str, bool]`: same, for plain messages (clearance).

### `AlertService` — `services/alert_service.py` (modify)
- Build `[TelegramNotifier, LineNotifier]` from config; create `ImgurClient` when `IMGUR_CLIENT_ID` is
  present and pass it into `LineNotifier`; wrap them in a `NotificationManager`.
- `run()` unchanged except notifications go through the manager: `send_all` per new alert,
  `send_message_all` for clearance. Per-strike behavior retained.

## Configuration

New keys per environment in `config.yaml` (PROD and STAGE):

| Key | Required | Purpose |
|-----|----------|---------|
| `LINE_CHANNEL_ACCESS_TOKEN` | yes | LINE channel access token (push auth) |
| `LINE_TO` | yes | Target user or group ID to push to |
| `IMGUR_CLIENT_ID` | for images | Imgur client ID; if absent, LINE sends text-only |

`config.py` validates that the required keys exist for the selected env and raises a clear error if any
are missing. No `LINE_CHANNEL_SECRET` — it is only needed to validate inbound webhook signatures, which
this project does not use.

## Error Handling

- Per-notifier isolation in `NotificationManager` (catch exceptions, coerce to `bool`).
- Configurable retry per notifier (default 1 retry).
- Imgur upload failure → LINE text-only fallback.
- `TelegramNotifier` now returns `bool` instead of raising.

## Dependencies

- Uses the existing `requests`.
- **Remove** `line-bot-sdk` and `pyimgur` from `requirements.txt` — pinned but unused; we call both APIs
  directly with `requests`, consistent with `TelegramNotifier`.

## Testing

Unit test per component; all HTTP mocked (`pytest-mock` / `unittest.mock`), no real API calls. Run with
`./venv/bin/python -m pytest`.

- `TelegramNotifier`: subclasses `Notifier`; success and failure paths return the right `bool`.
- `ImgurClient`: success returns URL; failure returns `None`.
- `LineNotifier`: subclasses `Notifier`; text-only; text+image; Imgur-failure fallback; alert formatting.
- `NotificationManager`: fan-out to multiple notifiers; retry on failure; independent failure; clearance.
- `config`: required keys present → ok; missing → raises.

## Known Limitations

Per-strike sending with images means each alert costs ~2 LINE message bubbles (text + image). LINE's free
push quota is limited (varies by plan/region), so an active storm can exhaust it quickly. Accepted for
this iteration; future mitigations include a per-run send cap or text-only LINE messages.

## Security

- Credentials live in `config.yaml` (existing pattern). Real tokens are currently committed there — treat
  them as secrets and rotate if exposed.
- Imgur-hosted radar images are publicly accessible by URL.
