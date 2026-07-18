"""Single source of all user-facing message text.

Notification bodies are Telegram-HTML (``<b>`` titles, escaped dynamic
fields); ``now`` is injectable everywhere for deterministic snapshot tests.
"""

import html as html_lib
from datetime import datetime
from zoneinfo import ZoneInfo

from domain.alert_checker import area_name_of
from models.alert import Alert
from infrastructure.state_repo import State
from infrastructure.utils import get_google_url

TW = ZoneInfo("Asia/Taipei")
CWA_LIGHTNING_URL = "https://www.cwa.gov.tw/V8/C/W/OBS_Lightning.html"

DIGEST_MAX_ROWS = 5
RECENT_MAX_ROWS = 10


def _now(now: datetime | None) -> datetime:
    return now if now is not None else datetime.now(TW)


def _esc(text) -> str:
    return html_lib.escape(str(text), quote=False)


def _hm(occur_time: str) -> str:
    """'YYYY-MM-DD HH:MM' -> 'HH:MM'."""
    return occur_time[-5:]


def _relative(occur_time: str, now: datetime) -> str:
    start = datetime.strptime(occur_time, "%Y-%m-%d %H:%M").replace(tzinfo=TW)
    delta = int((now - start).total_seconds())
    if delta < 60:
        return "剛剛"
    if delta < 3600:
        return f"約 {delta // 60} 分鐘前"
    return f"約 {delta // 3600} 小時前"


def _area_label(alert: Alert, areas: list[dict]) -> str:
    return area_name_of(alert.latitude, alert.longitude, areas) or "監測區"


def format_digest(alerts: list[Alert], areas: list[dict], now: datetime | None = None) -> str:
    """One message per detection round, however many strikes it found."""
    now = _now(now)
    newest_first = sorted(alerts, key=lambda a: a.occur_time, reverse=True)
    latest = newest_first[0]

    names: list[str] = []
    for alert in newest_first:
        label = _esc(_area_label(alert, areas))
        if label not in names:
            names.append(label)
    title = f"<b>⚡ 雷擊警報 — {'、'.join(names)}</b>"

    if len(newest_first) == 1:
        return (
            f"{title}\n"
            f"{_hm(latest.occur_time)}（{_relative(latest.occur_time, now)}）· {_esc(latest.category)}\n"
            f"位置 ({latest.latitude}, {latest.longitude})"
        )

    lines = [
        title,
        f"新增 {len(newest_first)} 筆落雷 · 最近一筆 {_hm(latest.occur_time)}"
        f"（{_relative(latest.occur_time, now)}）",
        "",
    ]
    for alert in newest_first[:DIGEST_MAX_ROWS]:
        lines.append(
            f"• {_hm(alert.occur_time)} {_esc(alert.category)}（{alert.latitude}, {alert.longitude}）"
        )
    if len(newest_first) > DIGEST_MAX_ROWS:
        lines.append(f"…另有 {len(newest_first) - DIGEST_MAX_ROWS} 筆")
    return "\n".join(lines)


def alert_buttons(alert: Alert) -> list[tuple[str, str]]:
    """Inline buttons for an alert message: map pin of the strike + CWA lightning page."""
    return [
        ("📍 開啟地圖", get_google_url(alert.latitude, alert.longitude)),
        ("🌩 CWA 雷達頁", CWA_LIGHTNING_URL),
    ]


def format_all_clear(
    episode_started: str | None, episode_count: int, now: datetime | None = None
) -> str:
    now = _now(now)
    line = f"解除 {now.strftime('%H:%M')}"
    if episode_started:
        start = datetime.strptime(episode_started, "%Y-%m-%d %H:%M").replace(tzinfo=TW)
        minutes = max(1, int((now - start).total_seconds()) // 60)
        line += f" · 本次警戒約 {minutes} 分鐘（共 {episode_count} 筆）"
    return f"<b>✅ 雷擊警報解除</b>\n{line}"


def status_text(state: State, areas: list[dict], now: datetime | None = None) -> str:
    now = _now(now)
    if state.active_alerts:
        latest = max(a.occur_time for a in state.active_alerts)
        alert_line = f"警戒：⚡ {len(state.active_alerts)} 筆活動落雷（最近 {_hm(latest)}）"
    else:
        alert_line = "警戒：無活動落雷 ✅"

    if state.last_check is None:
        check_line = "上次檢查：尚未執行"
    else:
        checked_at = datetime.fromisoformat(state.last_check.time).astimezone(TW).strftime("%H:%M:%S")
        if state.last_check.ok:
            check_line = f"上次檢查：{checked_at}（成功）"
        else:
            check_line = f"上次檢查：{checked_at}（失敗：{_esc(state.last_check.error or '未知錯誤')}）"

    area_names = "、".join(_esc(area["name"]) for area in areas)
    if state.is_muted(now):
        mute_line = f"通知：🔇 靜音至 {state.muted_until.astimezone(TW).strftime('%H:%M')}"
    else:
        mute_line = "通知：開啟"

    return (
        "📊 Thunder Monitor\n"
        f"{alert_line}\n"
        f"{check_line}\n"
        f"監測區：{area_names}\n"
        f"{mute_line}"
    )


def recent_text(state: State, areas: list[dict], now: datetime | None = None) -> str:
    entries = sorted(state.history, key=lambda a: a.occur_time, reverse=True)
    if not entries:
        return "🕐 近 24 小時內沒有落雷記錄 ✅"

    counts: dict[str, int] = {}
    for alert in entries:
        label = _esc(_area_label(alert, areas))
        counts[label] = counts.get(label, 0) + 1
    ordered = [_esc(area["name"]) for area in areas if _esc(area["name"]) in counts]
    ordered += [label for label in counts if label not in ordered]
    count_line = " · ".join(f"{label} {counts[label]} 筆" for label in ordered)

    lines = [f"🕐 近 24 小時落雷（{len(entries)} 筆）", count_line, ""]
    for alert in entries[:RECENT_MAX_ROWS]:
        lines.append(
            f"• {_hm(alert.occur_time)} {_esc(alert.category)}（{_esc(_area_label(alert, areas))}）"
        )
    if len(entries) > RECENT_MAX_ROWS:
        lines.append(f"…另有 {len(entries) - RECENT_MAX_ROWS} 筆")
    return "\n".join(lines)


def radar_caption(now: datetime | None = None) -> str:
    return f"🌩 雷達回波 {_now(now).strftime('%H:%M')}"


def mute_ack_text(until: datetime) -> str:
    return (
        f"🔇 已靜音至 {until.astimezone(TW).strftime('%H:%M')}。"
        "期間落雷照常記錄但不推播，/unmute 可提前恢復。"
    )


def unmute_ack_text() -> str:
    return "🔔 已恢復通知。"


def mute_usage_text() -> str:
    return "用法：/mute [分鐘]，例如 /mute 30（1–720）"


def help_text() -> str:
    return (
        "⚡ Thunder Monitor 指令\n"
        "/status — 目前警戒與系統狀態\n"
        "/radar — 即時雷達回波圖\n"
        "/recent — 近 24 小時落雷記錄\n"
        "/mute [分鐘] — 靜音通知（預設 30 分鐘）\n"
        "/unmute — 恢復通知\n"
        "/test — 發送測試警報\n"
        "/help — 本說明"
    )
