"""JSON-backed monitor state: active alerts, mute, episode, last check, 24h history.

Replaces the old JSONL ``alert.txt`` dedup store. A corrupt or partial
``state.json`` resets to an empty state (with a warning) rather than
wedging every subsequent run.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Union
from zoneinfo import ZoneInfo

from models.alert import Alert

STATE_FILE = Path("state.json")
TW = ZoneInfo("Asia/Taipei")
HISTORY_HOURS = 24
HISTORY_MAX = 200

logger = logging.getLogger(__name__)


@dataclass
class LastCheck:
    time: str  # ISO timestamp, Taipei tz
    ok: bool
    new_count: int
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {"time": self.time, "ok": self.ok, "new_count": self.new_count, "error": self.error}

    @classmethod
    def from_dict(cls, data: dict) -> "LastCheck":
        return cls(
            time=str(data["time"]),
            ok=bool(data["ok"]),
            new_count=int(data["new_count"]),
            error=data.get("error"),
        )


@dataclass
class State:
    active_alerts: list[Alert] = field(default_factory=list)
    muted_until: Optional[datetime] = None
    last_check: Optional[LastCheck] = None
    history: list[Alert] = field(default_factory=list)
    episode_started: Optional[str] = None  # occur_time of this episode's first strike
    episode_count: int = 0
    consecutive_failures: int = 0  # unbroken run of failed fetch rounds; gates the /fail ping

    def is_muted(self, now: Optional[datetime] = None) -> bool:
        now = now if now is not None else datetime.now(TW)
        return self.muted_until is not None and now < self.muted_until

    def prune_history(self, now: Optional[datetime] = None) -> None:
        """Drop history entries older than 24h and cap at the newest 200."""
        now = now if now is not None else datetime.now(TW)
        cutoff = now - timedelta(hours=HISTORY_HOURS)
        kept = []
        for alert in self.history:
            try:
                occurred = datetime.strptime(alert.occur_time, "%Y-%m-%d %H:%M").replace(tzinfo=TW)
            except ValueError:
                continue
            if occurred >= cutoff:
                kept.append(alert)
        self.history = kept[-HISTORY_MAX:]


def _load_alert_list(entries, label: str) -> list[Alert]:
    alerts: list[Alert] = []
    if not isinstance(entries, list):
        return alerts
    for i, entry in enumerate(entries, 1):
        try:
            alerts.append(Alert.from_dict(entry))
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Skipping malformed {label} entry {i}: {e}")
    return alerts


def load_state(path: Union[str, Path] = STATE_FILE) -> State:
    path = Path(path)
    if not path.exists():
        return State()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("state.json is not a JSON object")
    except (json.JSONDecodeError, ValueError, OSError) as e:
        logger.warning(f"Resetting corrupt state file {path}: {e}")
        return State()

    state = State(
        active_alerts=_load_alert_list(data.get("active_alerts"), "active alert"),
        history=_load_alert_list(data.get("history"), "history"),
        episode_started=data.get("episode_started"),
    )
    try:
        state.episode_count = int(data.get("episode_count") or 0)
    except (ValueError, TypeError):
        state.episode_count = 0
    try:
        state.consecutive_failures = int(data.get("consecutive_failures") or 0)
    except (ValueError, TypeError):
        state.consecutive_failures = 0
    muted = data.get("muted_until")
    if muted:
        try:
            state.muted_until = datetime.fromisoformat(muted)
        except (ValueError, TypeError) as e:
            logger.warning(f"Ignoring malformed muted_until: {e}")
    check = data.get("last_check")
    if isinstance(check, dict):
        try:
            state.last_check = LastCheck.from_dict(check)
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Ignoring malformed last_check: {e}")
    return state


def save_state(state: State, path: Union[str, Path] = STATE_FILE) -> None:
    data = {
        "active_alerts": [a.to_dict() for a in state.active_alerts],
        "muted_until": state.muted_until.isoformat() if state.muted_until else None,
        "last_check": state.last_check.to_dict() if state.last_check else None,
        "history": [a.to_dict() for a in state.history],
        "episode_started": state.episode_started,
        "episode_count": state.episode_count,
        "consecutive_failures": state.consecutive_failures,
    }
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
