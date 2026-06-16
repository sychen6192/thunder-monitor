# Notification UX Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the notification UX (unified message format, richer clearance message, relative time, delivery logging, config hardening) and add a testing strategy that verifies rendered messages without waiting for a real lightning strike.

**Architecture:** Extract a single `message_format` module both notifiers share. `AlertService` builds the clearance message from it and logs delivery results. `config.py` fails fast on missing/placeholder credentials. `app/main.py` gains a `--test` send mode and a stdlib-logging→loguru bridge. Tests use a synthetic CWA KML fixture and deterministic snapshots; the `--test` mode covers real-device visual checks.

**Tech Stack:** Python 3.11, `requests`, `loguru`, `lxml`, `pytest` + `unittest.mock`.

**Spec:** `docs/superpowers/specs/2026-06-16-ux-improvements-design.md`

---

## Conventions (apply to every task)

- **Run tests with:** `./venv/bin/python -m pytest` from the repo root. The venv's `pytest`/`pip` console scripts have a broken shebang; `-m` is required so the repo root is on `sys.path` (no `__init__.py`, no pytest config).
- **End every commit message** with: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- Branch is `feat/notification-ux` (already created). Fixtures `sample_alert`/`sample_alerts` live in `tests/conftest.py`.
- The pre-existing `get_google_url(longitude, latitude)` coordinate order is intentionally kept unchanged.

## File Structure

**New**
- `infrastructure/message_format.py` — `format_alert` / `format_clearance` (pure, `now`-injectable).
- `config.example.yaml` — committed credential template.
- `tests/fixtures/sample_thunder.kml` — synthetic CWA payload.
- `tests/unit/test_message_format.py`, `tests/unit/test_alert_checker.py`, `tests/unit/test_config_example.py`, `tests/unit/test_main.py`.

**Modified**
- `infrastructure/telegram_notifier.py`, `infrastructure/line_notifier.py` — use the shared formatter.
- `services/alert_service.py` — clearance via formatter + delivery logging.
- `infrastructure/config.py` — fail-fast validation + optional-key normalization.
- `app/main.py` — `--test` mode + loguru interception.
- `README.md` — setup instructions.
- `tests/unit/test_telegram_notifier.py`, `tests/unit/test_alert_service.py`, `tests/unit/test_config.py` — updated assertions.

---

## Task 1: Shared message formatter

**Files:**
- Create: `infrastructure/message_format.py`
- Test: `tests/unit/test_message_format.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_message_format.py`:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from infrastructure.message_format import format_alert, format_clearance

TW = ZoneInfo("Asia/Taipei")


def test_format_alert_exact(sample_alert):
    now = datetime(2024, 1, 1, 12, 3, tzinfo=TW)  # 3 minutes after occur_time
    assert format_alert(sample_alert, now=now) == (
        "⚡ 雷擊警報\n"
        "時間：2024-01-01 12:00（台灣時間 · 約 3 分鐘前）\n"
        "類型：Cloud-to-ground\n"
        "位置：25.0, 121.5\n"
        "地圖：https://www.google.com/maps?q=121.5,25.0"
    )


def test_format_alert_relative_buckets(sample_alert):
    assert "剛剛" in format_alert(sample_alert, now=datetime(2024, 1, 1, 12, 0, tzinfo=TW))
    assert "約 5 分鐘前" in format_alert(sample_alert, now=datetime(2024, 1, 1, 12, 5, tzinfo=TW))
    assert "約 2 小時前" in format_alert(sample_alert, now=datetime(2024, 1, 1, 14, 0, tzinfo=TW))


def test_format_clearance_with_duration():
    now = datetime(2024, 1, 1, 13, 5, tzinfo=TW)
    assert format_clearance(earliest_occur_time="2024-01-01 12:47", now=now) == (
        "✅ 雷擊警報解除\n"
        "解除時間：13:05（台灣時間）\n"
        "本次警戒約 18 分鐘（最早一筆 12:47）"
    )


def test_format_clearance_without_duration():
    now = datetime(2024, 1, 1, 13, 5, tzinfo=TW)
    assert format_clearance(now=now) == (
        "✅ 雷擊警報解除\n"
        "解除時間：13:05（台灣時間）"
    )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `./venv/bin/python -m pytest tests/unit/test_message_format.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'infrastructure.message_format'`.

- [ ] **Step 3: Create `infrastructure/message_format.py`**

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from models.alert import Alert
from infrastructure.utils import get_google_url

TW = ZoneInfo("Asia/Taipei")


def _now(now: datetime | None) -> datetime:
    return now if now is not None else datetime.now(TW)


def _relative(occur_time: str, now: datetime) -> str:
    start = datetime.strptime(occur_time, "%Y-%m-%d %H:%M").replace(tzinfo=TW)
    delta = int((now - start).total_seconds())
    if delta < 60:
        return "剛剛"
    if delta < 3600:
        return f"約 {delta // 60} 分鐘前"
    return f"約 {delta // 3600} 小時前"


def format_alert(alert: Alert, now: datetime | None = None) -> str:
    now = _now(now)
    return (
        "⚡ 雷擊警報\n"
        f"時間：{alert.occur_time}（台灣時間 · {_relative(alert.occur_time, now)}）\n"
        f"類型：{alert.category}\n"
        f"位置：{alert.latitude}, {alert.longitude}\n"
        f"地圖：{get_google_url(alert.longitude, alert.latitude)}"
    )


def format_clearance(earliest_occur_time: str | None = None, now: datetime | None = None) -> str:
    now = _now(now)
    lines = [
        "✅ 雷擊警報解除",
        f"解除時間：{now.strftime('%H:%M')}（台灣時間）",
    ]
    if earliest_occur_time:
        start = datetime.strptime(earliest_occur_time, "%Y-%m-%d %H:%M").replace(tzinfo=TW)
        minutes = max(1, int((now - start).total_seconds()) // 60)
        lines.append(f"本次警戒約 {minutes} 分鐘（最早一筆 {start.strftime('%H:%M')}）")
    return "\n".join(lines)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `./venv/bin/python -m pytest tests/unit/test_message_format.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add infrastructure/message_format.py tests/unit/test_message_format.py
git commit -m "feat: add shared message formatter with relative time and clearance context"
```

---

## Task 2: Notifiers use the shared formatter (unify format + Telegram header)

**Files:**
- Modify: `infrastructure/telegram_notifier.py`, `infrastructure/line_notifier.py`
- Test: `tests/unit/test_telegram_notifier.py`

- [ ] **Step 1: Add a failing assertion to the Telegram test**

In `tests/unit/test_telegram_notifier.py`, the test `test_send_formats_alert_and_delegates` currently ends with two asserts. Add a third asserting the unified header (Telegram has no header today):

```python
        sent_text = mock_send.call_args[0][0]
        assert sample_alert.occur_time in sent_text
        assert sample_alert.category in sent_text
        assert "⚡ 雷擊警報" in sent_text
```

- [ ] **Step 2: Run to verify it fails**

Run: `./venv/bin/python -m pytest tests/unit/test_telegram_notifier.py::test_send_formats_alert_and_delegates -v`
Expected: FAIL — current Telegram message has no `⚡ 雷擊警報` header.

- [ ] **Step 3: Rewrite both notifiers to use the shared formatter**

Replace `infrastructure/telegram_notifier.py` with:

```python
import logging

import requests

from models.alert import Alert
from infrastructure.notifier import Notifier
from infrastructure.message_format import format_alert

logger = logging.getLogger(__name__)


class TelegramNotifier(Notifier):
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id

    def send(self, alert: Alert, img_path: str | None = None) -> bool:
        return self.send_message(format_alert(alert), img_path)

    def send_message(self, message: str, img_path: str | None = None) -> bool:
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                data={"chat_id": self.chat_id, "text": message},
                timeout=10,
            )
            resp.raise_for_status()

            if img_path:
                with open(img_path, "rb") as photo:
                    resp = requests.post(
                        f"https://api.telegram.org/bot{self.token}/sendPhoto",
                        data={"chat_id": self.chat_id},
                        files={"photo": photo},
                        timeout=10,
                    )
                resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")
            return False
```

Replace `infrastructure/line_notifier.py` with:

```python
import json
import logging

import requests

from models.alert import Alert
from infrastructure.notifier import Notifier
from infrastructure.imgur_client import ImgurClient
from infrastructure.message_format import format_alert

logger = logging.getLogger(__name__)

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


class LineNotifier(Notifier):
    def __init__(
        self,
        channel_access_token: str,
        to: str,
        imgur_client: ImgurClient | None = None,
    ):
        self.channel_access_token = channel_access_token
        self.to = to
        self.imgur_client = imgur_client

    def send(self, alert: Alert, img_path: str | None = None) -> bool:
        return self._push(format_alert(alert), img_path)

    def send_message(self, message: str, img_path: str | None = None) -> bool:
        return self._push(message, img_path)

    def _push(self, text: str, img_path: str | None = None) -> bool:
        messages = [{"type": "text", "text": text}]

        if img_path and self.imgur_client:
            url = self.imgur_client.upload_image(img_path)
            if url:
                messages.append({
                    "type": "image",
                    "originalContentUrl": url,
                    "previewImageUrl": url,
                })
            else:
                logger.warning("Imgur upload failed; sending LINE text-only")

        try:
            resp = requests.post(
                LINE_PUSH_URL,
                headers={
                    "Authorization": f"Bearer {self.channel_access_token}",
                    "Content-Type": "application/json",
                },
                data=json.dumps({"to": self.to, "messages": messages}),
                timeout=10,
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"LINE notification failed: {e}")
            return False
```

- [ ] **Step 4: Run the notifier tests to verify they pass**

Run: `./venv/bin/python -m pytest tests/unit/test_telegram_notifier.py tests/unit/test_line_notifier.py -v`
Expected: PASS. Both notifiers now build text via `format_alert`, so Telegram gains the header and LINE's `test_send_formats_alert` (which asserts `雷擊警報`) still passes.

- [ ] **Step 5: Commit**

```bash
git add infrastructure/telegram_notifier.py infrastructure/line_notifier.py tests/unit/test_telegram_notifier.py
git commit -m "refactor: notifiers share message_format.format_alert (unified format)"
```

---

## Task 3: AlertService clearance message + delivery logging

**Files:**
- Modify: `services/alert_service.py`
- Test: `tests/unit/test_alert_service.py`

- [ ] **Step 1: Update the clearance test to expect the new message**

In `tests/unit/test_alert_service.py`, replace the last assertion of `test_run_clearance_sends_message`:

```python
        file_repo.reset_alerts.assert_called_once()
        call = service.notifier.send_message_all.call_args
        assert call.args[1] == "crop.jpg"
        assert call.args[0].startswith("✅ 雷擊警報解除")
```

- [ ] **Step 2: Run to verify it fails**

Run: `./venv/bin/python -m pytest tests/unit/test_alert_service.py::test_run_clearance_sends_message -v`
Expected: FAIL — current code sends the literal `"⚠️ 雷擊警報解除"`, which does not start with `✅`.

- [ ] **Step 3: Rewrite `services/alert_service.py`**

```python
from typing import Any

from loguru import logger

from domain.alert_checker import is_alert_valid
from infrastructure import cwb_client, image_processor, file_repo
from infrastructure.telegram_notifier import TelegramNotifier
from infrastructure.line_notifier import LineNotifier
from infrastructure.imgur_client import ImgurClient
from infrastructure.notification_manager import NotificationManager
from infrastructure.message_format import format_clearance


class AlertService:
    def __init__(self, config: dict[str, Any]) -> None:
        self.areas = config["AREAS"]
        self.token = config["CWB_TOKEN"]

        imgur_client = None
        if config.get("IMGUR_CLIENT_ID"):
            imgur_client = ImgurClient(config["IMGUR_CLIENT_ID"])

        notifiers = [
            TelegramNotifier(config["TELEGRAM_TOKEN"], config["TELEGRAM_CHAT_ID"]),
            LineNotifier(
                config["LINE_CHANNEL_ACCESS_TOKEN"],
                config["LINE_TO"],
                imgur_client=imgur_client,
            ),
        ]
        self.notifier = NotificationManager(notifiers)

    def run(self):
        prev_alerts = file_repo.load_alerts()
        doc = cwb_client.get_thunder_data(self.token)
        current_alerts = is_alert_valid(doc, self.areas)

        new_alerts = [a for a in current_alerts if a not in prev_alerts]

        if new_alerts:
            image_processor.download_thunder_img("crop.jpg")
            for alert in new_alerts:
                results = self.notifier.send_all(alert, "crop.jpg")
                logger.info("delivery {} -> {}", alert.occur_time, results)
            file_repo.save_alerts(current_alerts)
        elif not current_alerts and prev_alerts:
            file_repo.reset_alerts()
            image_processor.download_thunder_img("crop.jpg")
            earliest = min(a.occur_time for a in prev_alerts)
            results = self.notifier.send_message_all(
                format_clearance(earliest_occur_time=earliest), "crop.jpg"
            )
            logger.info("clearance delivery -> {}", results)
```

- [ ] **Step 4: Run the alert-service tests to verify they pass**

Run: `./venv/bin/python -m pytest tests/unit/test_alert_service.py -v`
Expected: PASS (all 5 tests). The new-alert tests are unaffected (the `logger.info` line works with a `Mock` result); the clearance test now sees the `✅` message.

- [ ] **Step 5: Commit**

```bash
git add services/alert_service.py tests/unit/test_alert_service.py
git commit -m "feat: richer clearance message and per-channel delivery logging"
```

---

## Task 4: Config fail-fast validation + optional-key normalization

**Files:**
- Modify: `infrastructure/config.py`
- Test: `tests/unit/test_config.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_config.py`:

```python
def test_load_config_placeholder_required_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = _valid_env()
    env["LINE_TO"] = "<your_line_user_or_group_id>"
    _write_config(tmp_path, {"PROD": env})
    with pytest.raises(ValueError, match="LINE_TO"):
        load_config("PROD")


def test_load_config_empty_required_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = _valid_env()
    env["TELEGRAM_TOKEN"] = "   "
    _write_config(tmp_path, {"PROD": env})
    with pytest.raises(ValueError, match="TELEGRAM_TOKEN"):
        load_config("PROD")


def test_load_config_placeholder_imgur_is_dropped(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = _valid_env()
    env["IMGUR_CLIENT_ID"] = "<your_imgur_client_id>"
    _write_config(tmp_path, {"PROD": env})
    assert "IMGUR_CLIENT_ID" not in load_config("PROD")


def test_load_config_real_imgur_kept(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = _valid_env()
    env["IMGUR_CLIENT_ID"] = "realid"
    _write_config(tmp_path, {"PROD": env})
    assert load_config("PROD")["IMGUR_CLIENT_ID"] == "realid"
```

- [ ] **Step 2: Run to verify they fail**

Run: `./venv/bin/python -m pytest tests/unit/test_config.py -v`
Expected: FAIL — the placeholder/empty tests don't raise yet (current code only checks key presence), and the imgur-drop test fails (current code never removes the key).

- [ ] **Step 3: Rewrite `infrastructure/config.py`**

```python
import yaml

REQUIRED_KEYS = [
    "TELEGRAM_TOKEN",
    "TELEGRAM_CHAT_ID",
    "CWB_TOKEN",
    "LOG",
    "AREAS",
    "LINE_CHANNEL_ACCESS_TOKEN",
    "LINE_TO",
]

OPTIONAL_KEYS = ["IMGUR_CLIENT_ID"]


def _is_unset(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        stripped = value.strip()
        return stripped == "" or (stripped.startswith("<") and stripped.endswith(">"))
    return False


def load_config(env: str = "PROD") -> dict:
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict):
        raise ValueError("config.yaml is empty or not a valid YAML mapping")

    if env not in config:
        raise ValueError(f"Environment '{env}' not found in config.yaml")

    env_config = config[env]

    missing = [key for key in REQUIRED_KEYS if key not in env_config or _is_unset(env_config[key])]
    if missing:
        raise ValueError(
            f"Missing or unset required config in {env}: {', '.join(missing)} "
            "(values must not be empty or <placeholders>)"
        )

    for key in OPTIONAL_KEYS:
        if key in env_config and _is_unset(env_config[key]):
            del env_config[key]

    return env_config
```

- [ ] **Step 4: Run the config tests to verify they pass**

Run: `./venv/bin/python -m pytest tests/unit/test_config.py -v`
Expected: PASS (all tests — the original 4 plus the 4 new ones).

- [ ] **Step 5: Commit**

```bash
git add infrastructure/config.py tests/unit/test_config.py
git commit -m "feat: config fails fast on missing/placeholder values; drops unset optional keys"
```

---

## Task 5: Config template + README setup

**Files:**
- Create: `config.example.yaml`, `tests/unit/test_config_example.py`
- Modify: `README.md`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_config_example.py`:

```python
import yaml

from infrastructure.config import REQUIRED_KEYS


def test_config_example_has_required_keys_for_both_envs():
    with open("config.example.yaml", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    for env in ("PROD", "STAGE"):
        assert env in data, f"missing env {env}"
        for key in REQUIRED_KEYS:
            assert key in data[env], f"{env} missing {key}"
```

- [ ] **Step 2: Run to verify it fails**

Run: `./venv/bin/python -m pytest tests/unit/test_config_example.py -v`
Expected: FAIL — `FileNotFoundError: config.example.yaml`.

- [ ] **Step 3: Create `config.example.yaml`**

```yaml
# Copy this file to config.yaml and fill in real credentials.
# config.yaml is gitignored — never commit real tokens.

PROD:
  DEBUG: False
  TELEGRAM_TOKEN: "<your_telegram_bot_token>"
  TELEGRAM_CHAT_ID: "<your_telegram_chat_id>"
  LINE_CHANNEL_ACCESS_TOKEN: "<your_line_channel_access_token>"
  LINE_TO: "<your_line_user_or_group_id>"
  IMGUR_CLIENT_ID: "<your_imgur_client_id>"   # optional: omit/placeholder => LINE sends text-only
  CWB_TOKEN: "<your_cwa_opendata_token>"
  LOG: ./log/thunder.log
  AREAS:
    - [22.65694, 22.598, 120.158, 120.3025]   # [top, down, left, right]

STAGE:
  DEBUG: True
  TELEGRAM_TOKEN: "<your_telegram_bot_token>"
  TELEGRAM_CHAT_ID: "<your_telegram_chat_id>"
  LINE_CHANNEL_ACCESS_TOKEN: "<your_line_channel_access_token>"
  LINE_TO: "<your_line_user_or_group_id>"
  IMGUR_CLIENT_ID: "<your_imgur_client_id>"
  CWB_TOKEN: "<your_cwa_opendata_token>"
  LOG: ./log/thunder_stage.log
  AREAS:
    - [23.76, 23.73, 120.58, 120.65]
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `./venv/bin/python -m pytest tests/unit/test_config_example.py -v`
Expected: PASS (1 test).

- [ ] **Step 5: Update `README.md`**

Replace the `## 🚀 How to Run` section's body with:

```markdown
## 🚀 How to Run

1. Install dependencies
   `./venv/bin/python -m pip install -r requirements.txt`

2. Create your config from the template and fill in credentials
   `cp config.example.yaml config.yaml` then edit `config.yaml`
   (`config.yaml` is gitignored. `IMGUR_CLIENT_ID` is optional — without it, LINE sends text-only.)

3. Send a test notification without waiting for real lightning (goes to STAGE)
   `./venv/bin/python app/main.py --test`

4. Run for real
   `./venv/bin/python app/main.py --env PROD`

## 🔔 Notifications

Alerts are pushed to both Telegram and LINE. LINE images are hosted via Imgur (HTTPS required by LINE).
Run the test suite with `./venv/bin/python -m pytest`.
```

- [ ] **Step 6: Commit**

```bash
git add config.example.yaml tests/unit/test_config_example.py README.md
git commit -m "docs: add config.example.yaml template and setup instructions"
```

---

## Task 6: Synthetic CWA fixture + parsing test

**Files:**
- Create: `tests/fixtures/sample_thunder.kml`, `tests/unit/test_alert_checker.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_alert_checker.py`:

```python
from pathlib import Path
from unittest.mock import patch

from lxml import html

from domain.alert_checker import is_alert_valid

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_thunder.kml"

# AREAS are [top, down, left, right]; _in_areas checks left<=lat<=right and down<=long<=top.
# The fixture stores coordinates as "經緯度: <first> , <second>" -> Alert(latitude=first, longitude=second).
AREAS = [[22.66, 22.59, 120.15, 120.31]]


def _doc():
    return html.fromstring(FIXTURE.read_bytes())


def test_is_alert_valid_keeps_in_area_recent():
    with patch("domain.alert_checker.diff_time", return_value=100):  # within 900s
        alerts = is_alert_valid(_doc(), AREAS)
    assert len(alerts) == 1
    assert alerts[0].category == "雲對地"
    assert alerts[0].latitude == 120.2
    assert alerts[0].longitude == 22.6


def test_is_alert_valid_drops_stale():
    with patch("domain.alert_checker.diff_time", return_value=5000):  # older than 900s
        alerts = is_alert_valid(_doc(), AREAS)
    assert alerts == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `./venv/bin/python -m pytest tests/unit/test_alert_checker.py -v`
Expected: FAIL — the fixture file does not exist yet (`OSError`/`FileNotFoundError` when reading it).

- [ ] **Step 3: Create `tests/fixtures/sample_thunder.kml`**

One in-area placemark (`120.2 , 22.6`) and one out-of-area placemark (`130.0 , 30.0`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Folder>
      <Placemark>
        <description>閃電種類:雲對地
時間:2024-01-01 12:00
經緯度: 120.2 , 22.6</description>
      </Placemark>
      <Placemark>
        <description>閃電種類:雲對雲
時間:2024-01-01 12:01
經緯度: 130.0 , 30.0</description>
      </Placemark>
    </Folder>
  </Document>
</kml>
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `./venv/bin/python -m pytest tests/unit/test_alert_checker.py -v`
Expected: PASS (2 tests). With `diff_time` mocked recent, only the in-area placemark survives; mocked stale, none survive.

If the parse returns 0 alerts unexpectedly, confirm the fixture's `<description>` text matches `_parse_alert`'s regex (`閃電種類:`, `時間:`, `經緯度: <a> , <b>` with spaces around the comma) — adjust the fixture text, not the test expectations.

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/sample_thunder.kml tests/unit/test_alert_checker.py
git commit -m "test: add synthetic CWA KML fixture and alert_checker parsing tests"
```

---

## Task 7: `--test` send mode + loguru interception

**Files:**
- Modify: `app/main.py`
- Test: `tests/unit/test_main.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_main.py`:

```python
import sys
from unittest.mock import Mock, patch

from app.main import parse_args, send_test_notifications


def test_parse_args_test_defaults_to_stage():
    with patch.object(sys, "argv", ["main.py", "--test"]):
        args = parse_args()
    assert args.test is True
    assert args.env == "STAGE"


def test_parse_args_test_respects_explicit_env():
    with patch.object(sys, "argv", ["main.py", "--test", "--env", "PROD"]):
        args = parse_args()
    assert args.env == "PROD"


def test_parse_args_default_is_prod_run():
    with patch.object(sys, "argv", ["main.py"]):
        args = parse_args()
    assert args.test is False
    assert args.env == "PROD"


def test_send_test_notifications_sends_alert_and_clearance():
    service = Mock()
    with patch("app.main.image_processor.download_thunder_img"):
        send_test_notifications(service)
    assert service.notifier.send_all.called
    assert service.notifier.send_message_all.called
    sent_alert = service.notifier.send_all.call_args[0][0]
    assert "測試" in sent_alert.category
```

- [ ] **Step 2: Run to verify it fails**

Run: `./venv/bin/python -m pytest tests/unit/test_main.py -v`
Expected: FAIL — `parse_args` has no `--test`/returns a string today, and `send_test_notifications` does not exist (`ImportError`).

- [ ] **Step 3: Rewrite `app/main.py`**

```python
import argparse
import logging
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from loguru import logger

from services.alert_service import AlertService
from infrastructure.config import load_config
from infrastructure import image_processor
from infrastructure.message_format import format_clearance
from models.alert import Alert


class InterceptHandler(logging.Handler):
    """Route stdlib logging records into loguru so infrastructure logs reach the LOG sink."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())


def main() -> None:
    args = parse_args()
    try:
        config = load_config(env=args.env)
        logger.add(config["LOG"], rotation="1 week")
        logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
        service = AlertService(config)
        if args.test:
            send_test_notifications(service)
        else:
            service.run()
    except Exception as e:
        logger.exception(e)


def send_test_notifications(service: AlertService) -> None:
    occur = (datetime.now(ZoneInfo("Asia/Taipei")) - timedelta(minutes=3)).strftime("%Y-%m-%d %H:%M")
    alert = Alert("Cloud-to-ground (測試)", occur, 25.0, 121.5)
    try:
        image_processor.download_thunder_img("crop.jpg")
        img = "crop.jpg"
    except Exception as e:
        logger.warning(f"test image download failed, sending without image: {e}")
        img = None
    logger.info("test alert delivery -> {}", service.notifier.send_all(alert, img))
    logger.info(
        "test clearance delivery -> {}",
        service.notifier.send_message_all(format_clearance(earliest_occur_time=occur), img),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Thunder Monitor")
    parser.add_argument("--env", default=None, choices=["PROD", "STAGE"], help="Environment config")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Send synthetic test notifications instead of fetching real data (defaults to STAGE)",
    )
    args = parser.parse_args()
    if args.env is None:
        args.env = "STAGE" if args.test else "PROD"
    return args


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `./venv/bin/python -m pytest tests/unit/test_main.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Run the full suite**

Run: `./venv/bin/python -m pytest -q`
Expected: all tests pass (the prior 59 plus the new message-format, config, config-example, alert-checker, and main tests).

- [ ] **Step 6: Commit**

```bash
git add app/main.py tests/unit/test_main.py
git commit -m "feat: add --test send mode and stdlib-logging to loguru bridge"
```

---

## Done criteria

- `./venv/bin/python -m pytest -q` is green.
- Telegram and LINE send the identical, header-led alert format with relative time.
- The clearance message includes clearance time and warning duration.
- `AlertService` logs per-channel delivery results, and those logs reach the LOG file.
- `config.py` rejects missing/empty/placeholder required values and drops an unset `IMGUR_CLIENT_ID`.
- `config.example.yaml` exists and stays in sync with `REQUIRED_KEYS` (enforced by a test).
- `./venv/bin/python app/main.py --test` sends a real Telegram + LINE alert and clearance pair to STAGE — verifiable on a phone without any real lightning.
