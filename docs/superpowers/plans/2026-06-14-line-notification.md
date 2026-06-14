# LINE Notification Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Push every lightning alert (and the "alert cleared" message) to LINE in addition to Telegram, with the radar image hosted on Imgur, behind a pluggable notifier abstraction.

**Architecture:** Strategy pattern. A `NotificationManager` fans each alert out to a list of `Notifier`s (`TelegramNotifier`, `LineNotifier`). `LineNotifier` uses an `ImgurClient` to turn the local `crop.jpg` into an HTTPS URL (LINE only accepts image URLs); it falls back to text-only if Imgur fails. One notifier failing never blocks the others. Per-strike sending is retained.

**Tech Stack:** Python 3.11, `requests` (raw HTTP — no SDKs), `pytest` + `unittest.mock`, `loguru`/`logging`.

**Spec:** `docs/superpowers/specs/2026-04-07-line-notification-design.md`

---

## Conventions (apply to every task)

- **Run tests with:** `./venv/bin/python -m pytest` — the `venv/` console scripts (`pytest`, `pip`) have a broken shebang (venv was created at an old path), and `-m` is required to put the repo root on `sys.path`. Run from the repo root.
- **End every commit message** with this trailer line:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- The `Notifier` ABC already exists at `infrastructure/notifier.py` with `send(alert, img_path=None) -> bool` and `send_message(message, img_path=None) -> bool`. Do not modify it.
- Fixtures `sample_alert` / `sample_alerts` already exist in `tests/conftest.py`.

## Preconditions

The working tree has uncommitted, already-passing groundwork (`infrastructure/file_repo.py`, `models/alert.py`, `tests/conftest.py`, `tests/unit/test_file_repo.py` — 32 tests green). Commit it first so feature work stays isolated:

- [ ] **Step 0: Verify green, then commit the groundwork**

```bash
./venv/bin/python -m pytest -q
git add infrastructure/file_repo.py models/alert.py tests/conftest.py tests/unit/test_file_repo.py
git commit -m "chore: commit file_repo and Alert serialization groundwork"
```
Expected: `32 passed` before committing.

## File Structure

**New files**
- `infrastructure/imgur_client.py` — upload a local image to Imgur, return its HTTPS URL (or `None`).
- `infrastructure/line_notifier.py` — `Notifier` for LINE push messaging; composes text + optional Imgur image.
- `infrastructure/notification_manager.py` — fan-out + per-notifier retry/isolation.
- `tests/unit/test_telegram_notifier.py`, `test_imgur_client.py`, `test_line_notifier.py`, `test_notification_manager.py`, `test_config.py`, `test_alert_service.py`

**Modified files**
- `infrastructure/telegram_notifier.py` — subclass `Notifier`, return `bool`, never raise.
- `infrastructure/config.py` — validate required keys (incl. new LINE keys).
- `config.yaml` — add `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_TO`, `IMGUR_CLIENT_ID` to PROD and STAGE.
- `services/alert_service.py` — build notifiers + `NotificationManager`, send through it.
- `requirements.txt` — remove unused `line-bot-sdk` and `pyimgur`.

---

## Task 1: TelegramNotifier implements Notifier

**Files:**
- Modify: `infrastructure/telegram_notifier.py`
- Test: `tests/unit/test_telegram_notifier.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_telegram_notifier.py`:

```python
from unittest.mock import patch
from infrastructure.telegram_notifier import TelegramNotifier
from infrastructure.notifier import Notifier


def test_telegram_notifier_implements_notifier():
    assert issubclass(TelegramNotifier, Notifier)


def test_send_message_success_returns_true():
    with patch("infrastructure.telegram_notifier.requests.post") as mock_post:
        mock_post.return_value.raise_for_status.return_value = None
        notifier = TelegramNotifier("token", "chat")
        assert notifier.send_message("hi") is True
        mock_post.assert_called_once()


def test_send_message_failure_returns_false():
    with patch("infrastructure.telegram_notifier.requests.post") as mock_post:
        mock_post.side_effect = Exception("boom")
        notifier = TelegramNotifier("token", "chat")
        assert notifier.send_message("hi") is False


def test_send_formats_alert_and_delegates(sample_alert):
    with patch.object(TelegramNotifier, "send_message", return_value=True) as mock_send:
        notifier = TelegramNotifier("token", "chat")
        assert notifier.send(sample_alert) is True
        mock_send.assert_called_once()
        sent_text = mock_send.call_args[0][0]
        assert sample_alert.occur_time in sent_text
        assert sample_alert.category in sent_text
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `./venv/bin/python -m pytest tests/unit/test_telegram_notifier.py -v`
Expected: FAIL — `test_telegram_notifier_implements_notifier` fails (TelegramNotifier is not a `Notifier` subclass) and the success/failure tests fail (current code returns `None` and re-raises).

- [ ] **Step 3: Rewrite `infrastructure/telegram_notifier.py`**

```python
import logging
import textwrap

import requests

from models.alert import Alert
from infrastructure.notifier import Notifier
from infrastructure.utils import get_google_url

logger = logging.getLogger(__name__)


class TelegramNotifier(Notifier):
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id

    def send(self, alert: Alert, img_path: str | None = None) -> bool:
        message = textwrap.dedent(f"""\
        時間：{alert.occur_time}
        類型：{alert.category}
        經緯度：({alert.latitude}, {alert.longitude})
        {get_google_url(alert.longitude, alert.latitude)}
        """)
        return self.send_message(message, img_path)

    def send_message(self, message: str, img_path: str | None = None) -> bool:
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                data={"chat_id": self.chat_id, "text": message},
            )
            resp.raise_for_status()

            if img_path:
                with open(img_path, "rb") as photo:
                    resp = requests.post(
                        f"https://api.telegram.org/bot{self.token}/sendPhoto",
                        data={"chat_id": self.chat_id},
                        files={"photo": photo},
                    )
                resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")
            return False
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `./venv/bin/python -m pytest tests/unit/test_telegram_notifier.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add infrastructure/telegram_notifier.py tests/unit/test_telegram_notifier.py
git commit -m "refactor: TelegramNotifier implements Notifier and returns bool"
```

---

## Task 2: ImgurClient

**Files:**
- Create: `infrastructure/imgur_client.py`
- Test: `tests/unit/test_imgur_client.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_imgur_client.py`:

```python
from unittest.mock import patch
from infrastructure.imgur_client import ImgurClient


def test_upload_image_success_returns_link(tmp_path):
    img = tmp_path / "crop.jpg"
    img.write_bytes(b"fake-bytes")
    with patch("infrastructure.imgur_client.requests.post") as mock_post:
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {"data": {"link": "https://i.imgur.com/x.jpg"}}
        client = ImgurClient("client-id")
        assert client.upload_image(str(img)) == "https://i.imgur.com/x.jpg"
        mock_post.assert_called_once()
        # client id goes in the auth header
        assert mock_post.call_args[1]["headers"]["Authorization"] == "Client-ID client-id"


def test_upload_image_api_failure_returns_none(tmp_path):
    img = tmp_path / "crop.jpg"
    img.write_bytes(b"fake-bytes")
    with patch("infrastructure.imgur_client.requests.post") as mock_post:
        mock_post.side_effect = Exception("boom")
        client = ImgurClient("client-id")
        assert client.upload_image(str(img)) is None


def test_upload_image_missing_file_returns_none():
    client = ImgurClient("client-id")
    assert client.upload_image("/no/such/file.jpg") is None
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `./venv/bin/python -m pytest tests/unit/test_imgur_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'infrastructure.imgur_client'`.

- [ ] **Step 3: Create `infrastructure/imgur_client.py`**

```python
import logging

import requests

logger = logging.getLogger(__name__)

IMGUR_UPLOAD_URL = "https://api.imgur.com/3/image"


class ImgurClient:
    def __init__(self, client_id: str):
        self.client_id = client_id

    def upload_image(self, image_path: str) -> str | None:
        try:
            with open(image_path, "rb") as image_file:
                resp = requests.post(
                    IMGUR_UPLOAD_URL,
                    headers={"Authorization": f"Client-ID {self.client_id}"},
                    files={"image": image_file},
                    timeout=10,
                )
            resp.raise_for_status()
            return resp.json()["data"]["link"]
        except Exception as e:
            logger.error(f"Imgur upload failed: {e}")
            return None
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `./venv/bin/python -m pytest tests/unit/test_imgur_client.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add infrastructure/imgur_client.py tests/unit/test_imgur_client.py
git commit -m "feat: add ImgurClient for image hosting"
```

---

## Task 3: LineNotifier

**Files:**
- Create: `infrastructure/line_notifier.py`
- Test: `tests/unit/test_line_notifier.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_line_notifier.py`:

```python
import json
from unittest.mock import Mock, patch

from infrastructure.line_notifier import LineNotifier
from infrastructure.notifier import Notifier


def test_line_notifier_implements_notifier():
    assert issubclass(LineNotifier, Notifier)


def test_send_message_text_only_success():
    with patch("infrastructure.line_notifier.requests.post") as mock_post:
        mock_post.return_value.raise_for_status.return_value = None
        notifier = LineNotifier("token", "U123", imgur_client=None)
        assert notifier.send_message("hello") is True
        payload = json.loads(mock_post.call_args[1]["data"])
        assert payload["to"] == "U123"
        assert len(payload["messages"]) == 1
        assert payload["messages"][0]["type"] == "text"


def test_send_with_image_appends_image_message():
    imgur = Mock()
    imgur.upload_image.return_value = "https://i.imgur.com/x.jpg"
    with patch("infrastructure.line_notifier.requests.post") as mock_post:
        mock_post.return_value.raise_for_status.return_value = None
        notifier = LineNotifier("token", "U123", imgur_client=imgur)
        assert notifier.send_message("hi", "crop.jpg") is True
        imgur.upload_image.assert_called_once_with("crop.jpg")
        payload = json.loads(mock_post.call_args[1]["data"])
        assert len(payload["messages"]) == 2
        assert payload["messages"][1]["type"] == "image"
        assert payload["messages"][1]["originalContentUrl"] == "https://i.imgur.com/x.jpg"


def test_send_with_image_falls_back_to_text_when_imgur_fails():
    imgur = Mock()
    imgur.upload_image.return_value = None
    with patch("infrastructure.line_notifier.requests.post") as mock_post:
        mock_post.return_value.raise_for_status.return_value = None
        notifier = LineNotifier("token", "U123", imgur_client=imgur)
        assert notifier.send_message("hi", "crop.jpg") is True
        payload = json.loads(mock_post.call_args[1]["data"])
        assert len(payload["messages"]) == 1
        assert payload["messages"][0]["type"] == "text"


def test_send_formats_alert(sample_alert):
    with patch("infrastructure.line_notifier.requests.post") as mock_post:
        mock_post.return_value.raise_for_status.return_value = None
        notifier = LineNotifier("token", "U123")
        assert notifier.send(sample_alert) is True
        payload = json.loads(mock_post.call_args[1]["data"])
        text = payload["messages"][0]["text"]
        assert sample_alert.category in text
        assert "雷擊警報" in text


def test_send_message_api_failure_returns_false():
    with patch("infrastructure.line_notifier.requests.post") as mock_post:
        mock_post.side_effect = Exception("boom")
        notifier = LineNotifier("token", "U123")
        assert notifier.send_message("hi") is False
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `./venv/bin/python -m pytest tests/unit/test_line_notifier.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'infrastructure.line_notifier'`.

- [ ] **Step 3: Create `infrastructure/line_notifier.py`**

```python
import json
import logging

import requests

from models.alert import Alert
from infrastructure.notifier import Notifier
from infrastructure.imgur_client import ImgurClient
from infrastructure.utils import get_google_url

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
        return self._push(self._format_alert(alert), img_path)

    def send_message(self, message: str, img_path: str | None = None) -> bool:
        return self._push(message, img_path)

    def _format_alert(self, alert: Alert) -> str:
        return (
            "⚡ 雷擊警報\n"
            f"時間：{alert.occur_time}\n"
            f"類型：{alert.category}\n"
            f"經緯度：({alert.latitude}, {alert.longitude})\n"
            f"{get_google_url(alert.longitude, alert.latitude)}"
        )

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

- [ ] **Step 4: Run the test to verify it passes**

Run: `./venv/bin/python -m pytest tests/unit/test_line_notifier.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add infrastructure/line_notifier.py tests/unit/test_line_notifier.py
git commit -m "feat: add LineNotifier with Imgur image support and text fallback"
```

---

## Task 4: NotificationManager

**Files:**
- Create: `infrastructure/notification_manager.py`
- Test: `tests/unit/test_notification_manager.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_notification_manager.py`:

```python
from infrastructure.notification_manager import NotificationManager
from infrastructure.notifier import Notifier


class OkA(Notifier):
    def send(self, alert, img_path=None): return True
    def send_message(self, message, img_path=None): return True


class OkB(Notifier):
    def send(self, alert, img_path=None): return True
    def send_message(self, message, img_path=None): return True


class FailFirst(Notifier):
    def __init__(self): self.calls = 0
    def send(self, alert, img_path=None):
        self.calls += 1
        return self.calls > 1
    def send_message(self, message, img_path=None): return True


class AlwaysFail(Notifier):
    def __init__(self): self.calls = 0
    def send(self, alert, img_path=None):
        self.calls += 1
        return False
    def send_message(self, message, img_path=None): return False


class Boom(Notifier):
    def send(self, alert, img_path=None): raise RuntimeError("boom")
    def send_message(self, message, img_path=None): raise RuntimeError("boom")


def test_send_all_reports_each_notifier(sample_alert):
    manager = NotificationManager([OkA(), OkB()])
    assert manager.send_all(sample_alert) == {"OkA": True, "OkB": True}


def test_retry_then_success(sample_alert):
    notifier = FailFirst()
    manager = NotificationManager([notifier], max_retries=1)
    assert manager.send_all(sample_alert) == {"FailFirst": True}
    assert notifier.calls == 2


def test_all_attempts_fail(sample_alert):
    notifier = AlwaysFail()
    manager = NotificationManager([notifier], max_retries=1)
    assert manager.send_all(sample_alert) == {"AlwaysFail": False}
    assert notifier.calls == 2


def test_one_failure_does_not_block_others(sample_alert):
    manager = NotificationManager([Boom(), OkA()], max_retries=0)
    assert manager.send_all(sample_alert) == {"Boom": False, "OkA": True}


def test_send_message_all():
    manager = NotificationManager([OkA(), OkB()])
    assert manager.send_message_all("hi") == {"OkA": True, "OkB": True}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `./venv/bin/python -m pytest tests/unit/test_notification_manager.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'infrastructure.notification_manager'`.

- [ ] **Step 3: Create `infrastructure/notification_manager.py`**

```python
import logging

from models.alert import Alert
from infrastructure.notifier import Notifier

logger = logging.getLogger(__name__)


class NotificationManager:
    def __init__(self, notifiers: list[Notifier], max_retries: int = 1):
        self.notifiers = notifiers
        self.max_retries = max_retries

    def send_all(self, alert: Alert, img_path: str | None = None) -> dict[str, bool]:
        return self._dispatch(lambda n: n.send(alert, img_path))

    def send_message_all(self, message: str, img_path: str | None = None) -> dict[str, bool]:
        return self._dispatch(lambda n: n.send_message(message, img_path))

    def _dispatch(self, action) -> dict[str, bool]:
        results: dict[str, bool] = {}
        for notifier in self.notifiers:
            name = type(notifier).__name__
            results[name] = self._with_retry(name, action, notifier)
        return results

    def _with_retry(self, name, action, notifier) -> bool:
        for attempt in range(self.max_retries + 1):
            try:
                if action(notifier):
                    return True
            except Exception as e:
                logger.error(f"{name} raised on attempt {attempt + 1}: {e}")
            if attempt < self.max_retries:
                logger.warning(f"Retrying {name} (attempt {attempt + 2})")
        logger.error(f"{name} failed after {self.max_retries + 1} attempt(s)")
        return False
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `./venv/bin/python -m pytest tests/unit/test_notification_manager.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add infrastructure/notification_manager.py tests/unit/test_notification_manager.py
git commit -m "feat: add NotificationManager for multi-channel fan-out with retry"
```

---

## Task 5: Config validation + new keys

**Files:**
- Modify: `infrastructure/config.py`
- Modify: `config.yaml`
- Test: `tests/unit/test_config.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_config.py`:

```python
import pytest
import yaml

from infrastructure.config import load_config


def _valid_env():
    return {
        "TELEGRAM_TOKEN": "t",
        "TELEGRAM_CHAT_ID": "c",
        "CWB_TOKEN": "w",
        "LOG": "./log/x.log",
        "AREAS": [[23.0, 22.0, 120.0, 121.0]],
        "LINE_CHANNEL_ACCESS_TOKEN": "la",
        "LINE_TO": "U1",
    }


def _write_config(dir_path, data):
    (dir_path / "config.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")


def test_load_config_returns_env_section(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_config(tmp_path, {"PROD": _valid_env()})
    assert load_config("PROD")["LINE_TO"] == "U1"


def test_load_config_missing_env_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_config(tmp_path, {"PROD": _valid_env()})
    with pytest.raises(ValueError, match="STAGE"):
        load_config("STAGE")


def test_load_config_missing_required_key_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    env = _valid_env()
    del env["LINE_TO"]
    _write_config(tmp_path, {"PROD": env})
    with pytest.raises(ValueError, match="LINE_TO"):
        load_config("PROD")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `./venv/bin/python -m pytest tests/unit/test_config.py -v`
Expected: FAIL — current `load_config` does not raise on missing env/keys; `test_load_config_missing_env_raises` and `test_load_config_missing_required_key_raises` fail (likely `KeyError`, not `ValueError`).

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


def load_config(env: str = "PROD") -> dict:
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if env not in config:
        raise ValueError(f"Environment '{env}' not found in config.yaml")

    env_config = config[env]
    missing = [key for key in REQUIRED_KEYS if key not in env_config]
    if missing:
        raise ValueError(f"Missing required config in {env}: {', '.join(missing)}")

    return env_config
```

Note: `IMGUR_CLIENT_ID` is intentionally NOT required — LINE degrades to text-only when it is absent.

- [ ] **Step 4: Run the test to verify it passes**

Run: `./venv/bin/python -m pytest tests/unit/test_config.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Add the new keys to `config.yaml`**

Under BOTH the `PROD:` and `STAGE:` blocks, add these three lines at the same indentation as the existing `TELEGRAM_TOKEN:` line (replace the angle-bracket placeholders with real credentials before running in production):

```yaml
  LINE_CHANNEL_ACCESS_TOKEN: "<your_line_channel_access_token>"
  LINE_TO: "<your_line_user_or_group_id>"
  IMGUR_CLIENT_ID: "<your_imgur_client_id>"
```

- [ ] **Step 6: Verify the real config still loads**

Run: `./venv/bin/python -c "from infrastructure.config import load_config; print(sorted(load_config('STAGE')))"`
Expected: prints a key list that includes `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_TO`, `IMGUR_CLIENT_ID`, and no exception.

- [ ] **Step 7: Commit**

```bash
git add infrastructure/config.py config.yaml tests/unit/test_config.py
git commit -m "feat: validate config and add LINE/Imgur keys"
```

---

## Task 6: Wire AlertService + drop unused deps

**Files:**
- Modify: `services/alert_service.py`
- Modify: `requirements.txt`
- Test: `tests/unit/test_alert_service.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_alert_service.py`:

```python
from unittest.mock import Mock, patch

from services.alert_service import AlertService


def _config():
    return {
        "AREAS": [[23.0, 22.0, 120.0, 121.0]],
        "CWB_TOKEN": "w",
        "TELEGRAM_TOKEN": "t",
        "TELEGRAM_CHAT_ID": "c",
        "LINE_CHANNEL_ACCESS_TOKEN": "la",
        "LINE_TO": "U1",
        "IMGUR_CLIENT_ID": "ic",
        "LOG": "./log/x.log",
    }


def test_init_builds_manager_with_telegram_and_line():
    service = AlertService(_config())
    names = [type(n).__name__ for n in service.notifier.notifiers]
    assert names == ["TelegramNotifier", "LineNotifier"]


def test_init_without_imgur_id_leaves_line_without_imgur():
    config = _config()
    del config["IMGUR_CLIENT_ID"]
    service = AlertService(config)
    assert service.notifier.notifiers[1].imgur_client is None


def test_run_sends_new_alerts(sample_alert):
    with patch("services.alert_service.file_repo") as file_repo, \
         patch("services.alert_service.cwb_client"), \
         patch("services.alert_service.image_processor") as image_processor, \
         patch("services.alert_service.is_alert_valid") as is_valid:
        file_repo.load_alerts.return_value = []
        is_valid.return_value = [sample_alert]

        service = AlertService(_config())
        service.notifier = Mock()
        service.run()

        image_processor.download_thunder_img.assert_called_once_with("crop.jpg")
        service.notifier.send_all.assert_called_once_with(sample_alert, "crop.jpg")
        file_repo.save_alerts.assert_called_once_with([sample_alert])


def test_run_clearance_sends_message(sample_alert):
    with patch("services.alert_service.file_repo") as file_repo, \
         patch("services.alert_service.cwb_client"), \
         patch("services.alert_service.image_processor"), \
         patch("services.alert_service.is_alert_valid") as is_valid:
        file_repo.load_alerts.return_value = [sample_alert]
        is_valid.return_value = []

        service = AlertService(_config())
        service.notifier = Mock()
        service.run()

        file_repo.reset_alerts.assert_called_once()
        service.notifier.send_message_all.assert_called_once_with("⚠️ 雷擊警報解除", "crop.jpg")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `./venv/bin/python -m pytest tests/unit/test_alert_service.py -v`
Expected: FAIL — `AlertService` builds a single `TelegramNotifier` (no `.notifier.notifiers`, no `send_all`).

- [ ] **Step 3: Rewrite `services/alert_service.py`**

```python
from typing import Any

from domain.alert_checker import is_alert_valid
from infrastructure import cwb_client, image_processor, file_repo
from infrastructure.telegram_notifier import TelegramNotifier
from infrastructure.line_notifier import LineNotifier
from infrastructure.imgur_client import ImgurClient
from infrastructure.notification_manager import NotificationManager


class AlertService:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
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
                self.notifier.send_all(alert, "crop.jpg")
            file_repo.save_alerts(current_alerts)
        elif not current_alerts and prev_alerts:
            file_repo.reset_alerts()
            image_processor.download_thunder_img("crop.jpg")
            self.notifier.send_message_all("⚠️ 雷擊警報解除", "crop.jpg")
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `./venv/bin/python -m pytest tests/unit/test_alert_service.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Remove unused dependencies from `requirements.txt`**

Delete the `line-bot-sdk==3.7.0` and `pyimgur==0.8.1` lines. The file should end with:

```text
requests==2.30.0
lxml==6.0.1
Pillow==11.3.0
PyYAML==6.0.2
loguru==0.7.0
cssselect==1.2.0
pytest==8.3.3
pytest-mock==3.14.0
```

- [ ] **Step 6: Run the full suite**

Run: `./venv/bin/python -m pytest -q`
Expected: all tests pass (32 groundwork + the new tests from Tasks 1–6).

- [ ] **Step 7: Commit**

```bash
git add services/alert_service.py requirements.txt tests/unit/test_alert_service.py
git commit -m "refactor: AlertService sends via NotificationManager; drop unused deps"
```

---

## Done criteria

- `./venv/bin/python -m pytest -q` is green.
- `AlertService` pushes each alert and the clearance message to both Telegram and LINE.
- LINE includes the radar image when `IMGUR_CLIENT_ID` is set, and degrades to text-only otherwise.
- A failure in one channel does not stop the other.
- Real LINE/Imgur credentials still need to be filled into `config.yaml` for a live end-to-end test (the tests mock all HTTP).
