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
    # boundaries: exactly 60s flips to 分鐘前, exactly 3600s flips to 小時前, negative delta stays 剛剛
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


def test_format_clearance_without_duration():
    now = datetime(2024, 1, 1, 13, 5, tzinfo=TW)
    assert format_clearance(now=now) == (
        "✅ 雷擊警報解除\n"
        "解除時間：13:05（台灣時間）"
    )
