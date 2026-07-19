import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from models.alert import Alert
from infrastructure.state_repo import State, load_state, save_state
from services.monitor import Monitor

TW = ZoneInfo("Asia/Taipei")
AREAS = [{"name": "高雄", "box": [22.7, 22.5, 120.1, 120.4]}]


def _occur(minutes_ago: int = 3) -> str:
    return (datetime.now(TW) - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%d %H:%M")


def _monitor(tmp_path, sender) -> Monitor:
    return Monitor(
        {"AREAS": AREAS, "CWB_TOKEN": "w"},
        sender,
        asyncio.Lock(),
        state_path=tmp_path / "state.json",
        radar_path=str(tmp_path / "crop.jpg"),
    )


def _sender() -> AsyncMock:
    sender = AsyncMock()
    sender.send_alert.return_value = True
    sender.send_text.return_value = True
    return sender


def _patches(valid_alerts, radar_path="crop.jpg"):
    return (
        patch("services.monitor.cwb_client.get_thunder_data"),
        patch("services.monitor.is_alert_valid", return_value=valid_alerts),
        patch("services.monitor.radar.download_radar", return_value=radar_path),
    )


async def test_new_alerts_send_single_digest_and_persist(tmp_path):
    sender = _sender()
    alerts = [Alert("雲對地", _occur(3), 22.6, 120.3), Alert("雲對雲", _occur(2), 22.61, 120.28)]
    fetch, valid, radar = _patches(alerts, str(tmp_path / "crop.jpg"))
    with fetch, valid, radar:
        result = await _monitor(tmp_path, sender).run_once()

    assert result.ok is True and result.new_count == 2
    sender.send_alert.assert_awaited_once()
    text = sender.send_alert.call_args.args[0]
    assert text.startswith("<b>⚡ 雷擊警報 — 高雄</b>")
    buttons = sender.send_alert.call_args.kwargs["buttons"]
    assert any("google.com/maps" in url for _, url in buttons)

    state = load_state(tmp_path / "state.json")
    assert state.active_alerts == alerts
    assert state.history == alerts
    assert state.episode_count == 2
    assert state.episode_started == min(a.occur_time for a in alerts)
    assert state.last_check.ok is True and state.last_check.new_count == 2


async def test_same_alerts_next_round_stay_silent(tmp_path):
    sender = _sender()
    alerts = [Alert("雲對地", _occur(3), 22.6, 120.3)]
    fetch, valid, radar = _patches(alerts, str(tmp_path / "crop.jpg"))
    monitor = _monitor(tmp_path, sender)
    with fetch, valid, radar:
        await monitor.run_once()
        result = await monitor.run_once()

    assert result.new_count == 0
    sender.send_alert.assert_awaited_once()  # only the first round notified
    sender.send_text.assert_not_awaited()
    assert load_state(tmp_path / "state.json").episode_count == 1


async def test_all_clear_notifies_and_resets_episode(tmp_path):
    sender = _sender()
    active = [Alert("雲對地", _occur(10), 22.6, 120.3)]
    save_state(
        State(active_alerts=active, episode_started=active[0].occur_time, episode_count=3),
        tmp_path / "state.json",
    )
    fetch, valid, radar = _patches([], str(tmp_path / "crop.jpg"))
    with fetch, valid, radar:
        result = await _monitor(tmp_path, sender).run_once()

    assert result.ok is True and result.new_count == 0
    sender.send_text.assert_awaited_once()
    text = sender.send_text.call_args.args[0]
    assert text.startswith("<b>✅ 雷擊警報解除</b>")
    assert "共 3 筆" in text

    state = load_state(tmp_path / "state.json")
    assert state.active_alerts == []
    assert state.episode_started is None and state.episode_count == 0


async def test_muted_round_records_but_does_not_send(tmp_path):
    sender = _sender()
    save_state(
        State(muted_until=datetime.now(TW) + timedelta(minutes=10)), tmp_path / "state.json"
    )
    alerts = [Alert("雲對地", _occur(3), 22.6, 120.3)]
    fetch, valid, radar = _patches(alerts, str(tmp_path / "crop.jpg"))
    with fetch, valid, radar:
        result = await _monitor(tmp_path, sender).run_once()

    assert result.ok is True and result.new_count == 1
    sender.send_alert.assert_not_awaited()
    sender.send_text.assert_not_awaited()
    state = load_state(tmp_path / "state.json")
    assert state.active_alerts == alerts  # still recorded
    assert state.episode_count == 1


async def test_fetch_failure_saves_error_and_keeps_state(tmp_path):
    sender = _sender()
    active = [Alert("雲對地", _occur(5), 22.6, 120.3)]
    save_state(State(active_alerts=active, episode_count=1), tmp_path / "state.json")
    with patch("services.monitor.cwb_client.get_thunder_data", side_effect=RuntimeError("api down")):
        result = await _monitor(tmp_path, sender).run_once()

    assert result.ok is False and "api down" in result.error
    sender.send_alert.assert_not_awaited()
    sender.send_text.assert_not_awaited()
    state = load_state(tmp_path / "state.json")
    assert state.active_alerts == active  # untouched
    assert state.last_check.ok is False and "api down" in state.last_check.error


def _monitor_with_healthcheck(tmp_path, sender, url) -> Monitor:
    return Monitor(
        {"AREAS": AREAS, "CWB_TOKEN": "w", "HEALTHCHECK_URL": url},
        sender,
        asyncio.Lock(),
        state_path=tmp_path / "state.json",
        radar_path=str(tmp_path / "crop.jpg"),
    )


async def test_successful_round_pings_healthcheck(tmp_path):
    sender = _sender()
    alerts = [Alert("雲對地", _occur(3), 22.6, 120.3)]
    fetch, valid, radar = _patches(alerts, str(tmp_path / "crop.jpg"))
    monitor = _monitor_with_healthcheck(tmp_path, sender, "https://hc-ping.com/abc")
    with fetch, valid, radar, \
         patch("services.monitor.healthcheck.ping", new_callable=AsyncMock) as ping:
        await monitor.run_once()
    ping.assert_awaited_once_with("https://hc-ping.com/abc", fail=False)


async def test_failed_round_pings_healthcheck_fail(tmp_path):
    sender = _sender()
    monitor = _monitor_with_healthcheck(tmp_path, sender, "https://hc-ping.com/abc")
    with patch("services.monitor.cwb_client.get_thunder_data", side_effect=RuntimeError("api down")), \
         patch("services.monitor.healthcheck.ping", new_callable=AsyncMock) as ping:
        await monitor.run_once()
    ping.assert_awaited_once_with("https://hc-ping.com/abc", fail=True)


async def test_radar_failure_degrades_to_text_only_digest(tmp_path):
    sender = _sender()
    alerts = [Alert("雲對地", _occur(3), 22.6, 120.3)]
    with patch("services.monitor.cwb_client.get_thunder_data"), \
         patch("services.monitor.is_alert_valid", return_value=alerts), \
         patch("services.monitor.radar.download_radar", side_effect=RuntimeError("503")):
        await _monitor(tmp_path, sender).run_once()

    sender.send_alert.assert_awaited_once()
    assert sender.send_alert.call_args.kwargs["img_path"] is None
