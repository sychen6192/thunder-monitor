import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from zoneinfo import ZoneInfo

from models.alert import Alert
from infrastructure.state_repo import State, load_state, save_state
from services.bot_commands import (
    MUTE_DEFAULT_MINUTES,
    RADAR_FAILED_TEXT,
    Commands,
    parse_mute_minutes,
)

TW = ZoneInfo("Asia/Taipei")
AREAS = [{"name": "高雄", "box": [22.7, 22.5, 120.1, 120.4]}]


def _commands(tmp_path, sender=None) -> Commands:
    return Commands(
        {"AREAS": AREAS},
        sender or AsyncMock(),
        asyncio.Lock(),
        state_path=tmp_path / "state.json",
        radar_path=str(tmp_path / "crop.jpg"),
    )


def _update(chat_id: int = 42) -> Mock:
    update = Mock()
    update.effective_message = AsyncMock()
    update.effective_chat.id = chat_id
    return update


def _context(args=None) -> Mock:
    context = Mock()
    context.args = args or []
    return context


# --- parse_mute_minutes ---


def test_parse_mute_defaults_without_args():
    assert parse_mute_minutes([]) == MUTE_DEFAULT_MINUTES


def test_parse_mute_accepts_valid_minutes():
    assert parse_mute_minutes(["60"]) == 60


def test_parse_mute_rejects_garbage_zero_and_over_cap():
    assert parse_mute_minutes(["abc"]) is None
    assert parse_mute_minutes(["0"]) is None
    assert parse_mute_minutes(["9999"]) is None


# --- handlers ---


async def test_status_replies_with_status_text(tmp_path):
    save_state(State(), tmp_path / "state.json")
    update = _update()
    await _commands(tmp_path).status(update, _context())
    text = update.effective_message.reply_text.call_args.args[0]
    assert text.startswith("📊 Thunder Monitor")
    assert "監測區：高雄" in text


async def test_recent_replies_empty_marker(tmp_path):
    update = _update()
    await _commands(tmp_path).recent(update, _context())
    assert "沒有落雷記錄" in update.effective_message.reply_text.call_args.args[0]


async def test_recent_prunes_stale_history_in_view(tmp_path):
    stale = (datetime.now(TW) - timedelta(hours=30)).strftime("%Y-%m-%d %H:%M")
    save_state(State(history=[Alert("雲對地", stale, 22.6, 120.3)]), tmp_path / "state.json")
    update = _update()
    await _commands(tmp_path).recent(update, _context())
    assert "沒有落雷記錄" in update.effective_message.reply_text.call_args.args[0]


async def test_mute_sets_state_and_acks(tmp_path):
    update = _update()
    await _commands(tmp_path).mute(update, _context(["60"]))
    state = load_state(tmp_path / "state.json")
    expected = datetime.now(TW) + timedelta(minutes=60)
    assert state.muted_until is not None
    assert abs((state.muted_until - expected).total_seconds()) < 5
    assert "已靜音至" in update.effective_message.reply_text.call_args.args[0]


async def test_mute_invalid_arg_replies_usage_and_leaves_state(tmp_path):
    update = _update()
    await _commands(tmp_path).mute(update, _context(["abc"]))
    assert "用法" in update.effective_message.reply_text.call_args.args[0]
    assert load_state(tmp_path / "state.json").muted_until is None


async def test_unmute_clears_state(tmp_path):
    save_state(
        State(muted_until=datetime.now(TW) + timedelta(minutes=30)), tmp_path / "state.json"
    )
    update = _update()
    await _commands(tmp_path).unmute(update, _context())
    assert load_state(tmp_path / "state.json").muted_until is None
    assert "已恢復通知" in update.effective_message.reply_text.call_args.args[0]


async def test_radar_replies_photo_with_caption(tmp_path):
    img = tmp_path / "crop.jpg"

    def _fake_download(path):
        img.write_bytes(b"jpg")
        return str(img)

    update = _update()
    with patch("services.bot_commands.radar.download_radar", side_effect=_fake_download):
        await _commands(tmp_path).radar(update, _context())
    kwargs = update.effective_message.reply_photo.call_args.kwargs
    assert kwargs["caption"].startswith("🌩 雷達回波")


async def test_radar_failure_replies_error_text(tmp_path):
    update = _update()
    with patch("services.bot_commands.radar.download_radar", side_effect=RuntimeError("503")):
        await _commands(tmp_path).radar(update, _context())
    assert update.effective_message.reply_text.call_args.args[0] == RADAR_FAILED_TEXT


async def test_test_command_pushes_marked_digest_through_sender(tmp_path):
    sender = AsyncMock()
    sender.send_alert.return_value = True
    commands = _commands(tmp_path, sender)
    with patch("services.bot_commands.radar.download_radar", side_effect=RuntimeError("503")):
        await commands.test(_update(), _context())
    sender.send_alert.assert_awaited_once()
    text = sender.send_alert.call_args.args[0]
    assert "測試" in text and text.startswith("<b>⚡ 雷擊警報 — 高雄</b>")
    assert sender.send_alert.call_args.kwargs["img_path"] is None


async def test_test_command_replies_in_the_chat_that_asked(tmp_path):
    # Running /test from a DM must not push the synthetic alert into the alert group.
    sender = AsyncMock()
    sender.send_alert.return_value = True
    commands = _commands(tmp_path, sender)
    with patch("services.bot_commands.radar.download_radar", side_effect=RuntimeError("no net")):
        await commands.test(_update(chat_id=6006055946), _context())
    assert sender.send_alert.call_args.kwargs["chat_id"] == 6006055946


async def test_test_command_without_update_uses_push_target(tmp_path):
    # The CLI --test path has no originating chat and must fall back to the push chat.
    sender = AsyncMock()
    sender.send_alert.return_value = True
    commands = _commands(tmp_path, sender)
    with patch("services.bot_commands.radar.download_radar", side_effect=RuntimeError("no net")):
        await commands.test(None, None)
    assert sender.send_alert.call_args.kwargs["chat_id"] is None


async def test_help_lists_commands(tmp_path):
    update = _update()
    await _commands(tmp_path).help(update, _context())
    text = update.effective_message.reply_text.call_args.args[0]
    assert "/mute" in text and "/radar" in text
