"""JSONL-backed store for the previous run's alerts (deduplication state).

One alert per line; ``alert.txt`` lives in the current working directory.
"""

import json
import logging
from pathlib import Path

from models.alert import Alert

ALERT_FILE = Path("alert.txt")

logger = logging.getLogger(__name__)


def save_alerts(alerts: list[Alert]) -> None:
    """Overwrite the store with ``alerts`` (one JSON object per line).

    An empty list clears the file. I/O errors propagate to the caller.
    """
    ALERT_FILE.write_text(
        "".join(json.dumps(a.to_dict()) + "\n" for a in alerts),
        encoding="utf-8",
    )


def load_alerts() -> list[Alert]:
    """Return the stored alerts.

    Malformed lines are skipped (with a warning) rather than aborting the
    load — a previous run that crashed mid-write can leave a truncated last
    line, and one bad line should not wedge every subsequent run.
    """
    if not ALERT_FILE.exists():
        return []
    alerts: list[Alert] = []
    with open(ALERT_FILE, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                alerts.append(Alert.from_dict(json.loads(line)))
            except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
                logger.warning(f"Skipping malformed alert on line {line_num}: {e}")
    return alerts


def reset_alerts() -> None:
    """Clear the store."""
    ALERT_FILE.write_text("")
