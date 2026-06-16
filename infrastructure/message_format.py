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
