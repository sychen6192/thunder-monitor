import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from models.alert import Alert
from infrastructure.state_repo import HISTORY_MAX, LastCheck, State, load_state, save_state

TW = ZoneInfo("Asia/Taipei")
NOW = datetime(2024, 1, 2, 12, 0, tzinfo=TW)


def test_round_trip_full_state(tmp_path, sample_alerts):
    path = tmp_path / "state.json"
    state = State(
        active_alerts=sample_alerts,
        muted_until=NOW + timedelta(minutes=30),
        last_check=LastCheck(time=NOW.isoformat(), ok=True, new_count=2),
        history=sample_alerts,
        episode_started="2024-01-01 12:00",
        episode_count=5,
    )
    save_state(state, path)
    loaded = load_state(path)
    assert loaded == state


def test_missing_file_returns_empty_state(tmp_path):
    state = load_state(tmp_path / "absent.json")
    assert state == State()


def test_corrupt_json_resets(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{not json", encoding="utf-8")
    assert load_state(path) == State()


def test_non_object_json_resets(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("[1, 2]", encoding="utf-8")
    assert load_state(path) == State()


def test_partial_state_gets_defaults(tmp_path, sample_alert):
    path = tmp_path / "state.json"
    path.write_text(json.dumps({"active_alerts": [sample_alert.to_dict()]}), encoding="utf-8")
    state = load_state(path)
    assert state.active_alerts == [sample_alert]
    assert state.muted_until is None
    assert state.last_check is None
    assert state.history == []
    assert state.episode_count == 0


def test_malformed_entries_are_skipped(tmp_path, sample_alert):
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps(
            {
                "active_alerts": [sample_alert.to_dict(), {"category": "broken"}],
                "muted_until": "not-a-timestamp",
            }
        ),
        encoding="utf-8",
    )
    state = load_state(path)
    assert state.active_alerts == [sample_alert]
    assert state.muted_until is None


def test_is_muted_before_and_after_expiry():
    state = State(muted_until=NOW + timedelta(minutes=10))
    assert state.is_muted(now=NOW) is True
    assert state.is_muted(now=NOW + timedelta(minutes=11)) is False
    assert State().is_muted(now=NOW) is False


def test_prune_history_drops_old_and_caps():
    fresh_time = (NOW - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
    stale_time = (NOW - timedelta(hours=25)).strftime("%Y-%m-%d %H:%M")
    fresh = [Alert("c", fresh_time, 22.6, 120.2) for _ in range(HISTORY_MAX + 5)]
    stale = [Alert("c", stale_time, 22.6, 120.2)]
    state = State(history=stale + fresh)
    state.prune_history(now=NOW)
    assert len(state.history) == HISTORY_MAX
    assert all(a.occur_time == fresh_time for a in state.history)


def test_prune_history_skips_unparseable_times():
    state = State(history=[Alert("c", "garbage", 22.6, 120.2)])
    state.prune_history(now=NOW)
    assert state.history == []
