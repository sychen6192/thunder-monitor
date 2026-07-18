from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from models.alert import Alert
from infrastructure.message_format import (
    CWA_LIGHTNING_URL,
    alert_buttons,
    format_alert,
    format_all_clear,
    format_clearance,
    format_digest,
    help_text,
    mute_ack_text,
    radar_caption,
    recent_text,
    status_text,
)
from infrastructure.state_repo import LastCheck, State

TW = ZoneInfo("Asia/Taipei")
AREAS = [
    {"name": "高雄", "box": [22.7, 22.5, 120.1, 120.4]},
    {"name": "台南", "box": [23.2, 22.9, 120.0, 120.4]},
]


def _kh(category: str, occur: str, lat: float, long: float) -> Alert:
    return Alert(category, occur, lat, long)


# --- format_digest ---


def test_digest_multi_exact():
    now = datetime(2024, 1, 1, 15, 49, tzinfo=TW)
    alerts = [
        _kh("雲對地", "2024-01-01 15:44", 22.6, 120.3),
        _kh("雲對雲", "2024-01-01 15:45", 22.61, 120.27),
        _kh("雲對地", "2024-01-01 15:47", 22.63, 120.29),
    ]
    assert format_digest(alerts, AREAS, now=now) == (
        "<b>⚡ 雷擊警報 — 高雄</b>\n"
        "新增 3 筆落雷 · 最近一筆 15:47（約 2 分鐘前）\n"
        "\n"
        "• 15:47 雲對地（22.63, 120.29）\n"
        "• 15:45 雲對雲（22.61, 120.27）\n"
        "• 15:44 雲對地（22.6, 120.3）"
    )


def test_digest_single_exact():
    now = datetime(2024, 1, 1, 15, 49, tzinfo=TW)
    alerts = [_kh("雲對地", "2024-01-01 15:47", 22.63, 120.29)]
    assert format_digest(alerts, AREAS, now=now) == (
        "<b>⚡ 雷擊警報 — 高雄</b>\n"
        "15:47（約 2 分鐘前）· 雲對地\n"
        "位置 (22.63, 120.29)"
    )


def test_digest_caps_rows_and_reports_overflow():
    now = datetime(2024, 1, 1, 16, 0, tzinfo=TW)
    alerts = [_kh("雲對地", f"2024-01-01 15:{40 + i}", 22.6, 120.3) for i in range(7)]
    text = format_digest(alerts, AREAS, now=now)
    assert text.count("•") == 5
    assert text.endswith("…另有 2 筆")
    assert "15:46" in text and "15:41" not in text  # newest five kept


def test_digest_lists_all_involved_areas_in_title():
    now = datetime(2024, 1, 1, 16, 0, tzinfo=TW)
    alerts = [
        _kh("雲對地", "2024-01-01 15:47", 22.6, 120.3),   # 高雄
        _kh("雲對地", "2024-01-01 15:46", 23.0, 120.2),   # 台南
    ]
    assert format_digest(alerts, AREAS, now=now).startswith("<b>⚡ 雷擊警報 — 高雄、台南</b>")


def test_digest_out_of_area_falls_back():
    now = datetime(2024, 1, 1, 16, 0, tzinfo=TW)
    alerts = [_kh("雲對地（測試）", "2024-01-01 15:47", 30.0, 130.0)]
    assert "監測區" in format_digest(alerts, AREAS, now=now)


def test_digest_escapes_html():
    now = datetime(2024, 1, 1, 16, 0, tzinfo=TW)
    alerts = [_kh("<b>bad</b>", "2024-01-01 15:47", 22.6, 120.3)]
    text = format_digest(alerts, AREAS, now=now)
    assert "<b>bad</b>" not in text
    assert "&lt;b&gt;bad&lt;/b&gt;" in text


def test_alert_buttons_use_strike_location():
    buttons = alert_buttons(_kh("雲對地", "2024-01-01 15:47", 22.63, 120.29))
    assert buttons == [
        ("📍 開啟地圖", "https://www.google.com/maps?q=22.63,120.29"),
        ("🌩 CWA 雷達頁", CWA_LIGHTNING_URL),
    ]


# --- format_all_clear ---


def test_all_clear_exact():
    now = datetime(2024, 1, 1, 16, 8, tzinfo=TW)
    assert format_all_clear("2024-01-01 15:47", 5, now=now) == (
        "<b>✅ 雷擊警報解除</b>\n"
        "解除 16:08 · 本次警戒約 21 分鐘（共 5 筆）"
    )


def test_all_clear_without_episode_start():
    now = datetime(2024, 1, 1, 16, 8, tzinfo=TW)
    assert format_all_clear(None, 0, now=now) == "<b>✅ 雷擊警報解除</b>\n解除 16:08"


# --- status_text ---


def test_status_idle_exact():
    now = datetime(2024, 1, 1, 16, 5, tzinfo=TW)
    state = State(last_check=LastCheck(time="2024-01-01T16:04:32+08:00", ok=True, new_count=0))
    assert status_text(state, AREAS, now=now) == (
        "📊 Thunder Monitor\n"
        "警戒：無活動落雷 ✅\n"
        "上次檢查：16:04:32（成功）\n"
        "監測區：高雄、台南\n"
        "通知：開啟"
    )


def test_status_active_muted_and_failed_check():
    now = datetime(2024, 1, 1, 16, 5, tzinfo=TW)
    state = State(
        active_alerts=[
            _kh("雲對地", "2024-01-01 15:44", 22.6, 120.3),
            _kh("雲對地", "2024-01-01 15:47", 22.63, 120.29),
        ],
        muted_until=datetime(2024, 1, 1, 16, 35, tzinfo=TW),
        last_check=LastCheck(time="2024-01-01T16:04:32+08:00", ok=False, new_count=0, error="boom"),
    )
    assert status_text(state, AREAS, now=now) == (
        "📊 Thunder Monitor\n"
        "警戒：⚡ 2 筆活動落雷（最近 15:47）\n"
        "上次檢查：16:04:32（失敗：boom）\n"
        "監測區：高雄、台南\n"
        "通知：🔇 靜音至 16:35"
    )


def test_status_never_checked():
    now = datetime(2024, 1, 1, 16, 5, tzinfo=TW)
    assert "上次檢查：尚未執行" in status_text(State(), AREAS, now=now)


# --- recent_text ---


def test_recent_empty():
    assert recent_text(State(), AREAS) == "🕐 近 24 小時內沒有落雷記錄 ✅"


def test_recent_exact():
    state = State(
        history=[
            _kh("雲對地", "2024-01-01 15:44", 22.6, 120.3),    # 高雄
            _kh("雲對雲", "2024-01-01 15:45", 23.0, 120.2),    # 台南
            _kh("雲對地", "2024-01-01 15:47", 22.63, 120.29),  # 高雄
        ]
    )
    assert recent_text(state, AREAS) == (
        "🕐 近 24 小時落雷（3 筆）\n"
        "高雄 2 筆 · 台南 1 筆\n"
        "\n"
        "• 15:47 雲對地（高雄）\n"
        "• 15:45 雲對雲（台南）\n"
        "• 15:44 雲對地（高雄）"
    )


def test_recent_caps_rows():
    state = State(
        history=[_kh("雲對地", f"2024-01-01 12:{i:02d}", 22.6, 120.3) for i in range(13)]
    )
    text = recent_text(state, AREAS)
    assert text.count("•") == 10
    assert text.endswith("…另有 3 筆")


# --- small texts ---


def test_radar_caption():
    assert radar_caption(datetime(2024, 1, 1, 16, 5, tzinfo=TW)) == "🌩 雷達回波 16:05"


def test_mute_ack_text():
    until = datetime(2024, 1, 1, 16, 35, tzinfo=TW)
    assert mute_ack_text(until) == (
        "🔇 已靜音至 16:35。期間落雷照常記錄但不推播，/unmute 可提前恢復。"
    )


def test_help_text_lists_all_commands():
    text = help_text()
    for command in ("/status", "/radar", "/recent", "/mute", "/unmute", "/test", "/help"):
        assert command in text


# --- legacy formats (kept until the old AlertService path is removed) ---


def test_format_alert_exact(sample_alert):
    now = datetime(2024, 1, 1, 12, 3, tzinfo=TW)  # 3 minutes after occur_time
    assert format_alert(sample_alert, now=now) == (
        "⚡ 雷擊警報\n"
        "時間：2024-01-01 12:00（台灣時間 · 約 3 分鐘前）\n"
        "類型：Cloud-to-ground\n"
        "位置：25.0, 121.5\n"
        "地圖：https://www.google.com/maps?q=25.0,121.5"
    )


def test_format_alert_relative_buckets(sample_alert):
    assert "剛剛" in format_alert(sample_alert, now=datetime(2024, 1, 1, 12, 0, tzinfo=TW))
    assert "約 5 分鐘前" in format_alert(sample_alert, now=datetime(2024, 1, 1, 12, 5, tzinfo=TW))
    assert "約 2 小時前" in format_alert(sample_alert, now=datetime(2024, 1, 1, 14, 0, tzinfo=TW))
    assert "約 1 分鐘前" in format_alert(sample_alert, now=datetime(2024, 1, 1, 12, 1, tzinfo=TW))
    assert "約 1 小時前" in format_alert(sample_alert, now=datetime(2024, 1, 1, 13, 0, tzinfo=TW))
    assert "剛剛" in format_alert(sample_alert, now=datetime(2024, 1, 1, 11, 59, tzinfo=TW))


def test_format_clearance_with_duration():
    now = datetime(2024, 1, 1, 13, 5, tzinfo=TW)
    assert format_clearance(earliest_occur_time="2024-01-01 12:47", now=now) == (
        "✅ 雷擊警報解除\n"
        "解除時間：13:05（台灣時間）\n"
        "本次警戒約 18 分鐘（最早一筆 12:47）"
    )
