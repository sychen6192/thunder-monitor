from pathlib import Path
from domain.models import Alert

import json

ALERT_FILE = Path("alert.txt")


def save_alerts(alerts: list[Alert]) -> None:
    with open(ALERT_FILE, "w", encoding="utf-8") as f:
        for alert in alerts:
            f.write(json.dumps(alert.__dict__) + "\n")

def load_alerts() -> list[Alert]:
    if not ALERT_FILE.exists():
        return []
    with open(ALERT_FILE, encoding="utf-8") as f:
        return [Alert(**json.loads(line)) for line in f if line.strip()]

def reset_alerts() -> None:
    ALERT_FILE.write_text("")
