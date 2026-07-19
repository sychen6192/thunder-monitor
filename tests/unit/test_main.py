import logging
import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from loguru import logger
from telegram import Chat, Message, Update, User
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from app.main import InterceptHandler, command_filter, parse_args, register_handlers, run_test
from services.bot_commands import Commands


def test_parse_args_test_defaults_to_stage():
    with patch.object(sys, "argv", ["main.py", "--test"]):
        args = parse_args()
    assert args.test is True
    assert args.env == "STAGE"


def test_parse_args_test_respects_explicit_env():
    with patch.object(sys, "argv", ["main.py", "--test", "--env", "PROD"]):
        args = parse_args()
    assert args.env == "PROD"
    assert args.test is True


def test_parse_args_default_is_prod_daemon():
    with patch.object(sys, "argv", ["main.py"]):
        args = parse_args()
    assert args.test is False
    assert args.once is False
    assert args.env == "PROD"


def test_parse_args_once_defaults_to_prod():
    with patch.object(sys, "argv", ["main.py", "--once"]):
        args = parse_args()
    assert args.once is True
    assert args.env == "PROD"


GROUP_ID = -1001234
MY_USER_ID = 6006055946
STRANGER_ID = 999999


def _incoming(chat_id: int, user_id: int) -> Update:
    """A real Update, so the filters are exercised the way PTB will use them."""
    chat = Chat(id=chat_id, type=Chat.GROUP if chat_id < 0 else Chat.PRIVATE)
    message = Message(
        message_id=1,
        date=datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc),
        chat=chat,
        from_user=User(id=user_id, is_bot=False, first_name="tester"),
        text="/status",
    )
    return Update(update_id=1, message=message)


def test_command_filter_allows_the_push_chat():
    f = command_filter({"TELEGRAM_CHAT_ID": str(GROUP_ID)})
    assert bool(f.check_update(_incoming(GROUP_ID, STRANGER_ID)))


def test_command_filter_blocks_other_chats_by_default():
    f = command_filter({"TELEGRAM_CHAT_ID": str(GROUP_ID)})
    assert not bool(f.check_update(_incoming(MY_USER_ID, MY_USER_ID)))


def test_command_filter_allows_listed_user_in_private_chat():
    f = command_filter({"TELEGRAM_CHAT_ID": str(GROUP_ID), "COMMAND_USER_IDS": [MY_USER_ID]})
    assert bool(f.check_update(_incoming(MY_USER_ID, MY_USER_ID)))


def test_command_filter_still_blocks_strangers_when_users_listed():
    f = command_filter({"TELEGRAM_CHAT_ID": str(GROUP_ID), "COMMAND_USER_IDS": [MY_USER_ID]})
    assert not bool(f.check_update(_incoming(STRANGER_ID, STRANGER_ID)))


def test_command_filter_username_fallback():
    f = command_filter({"TELEGRAM_CHAT_ID": "@mychannel"})
    assert isinstance(f, filters.Chat)
    assert "mychannel" in f.usernames


def test_register_handlers_whitelists_commands_and_logs_strangers():
    app = Application.builder().token("123:abc").build()
    commands = Commands(
        {"AREAS": [{"name": "x", "box": [1.0, 0.0, 0.0, 1.0]}]},
        sender=AsyncMock(),
        lock=None,
    )
    register_handlers(app, commands, command_filter({"TELEGRAM_CHAT_ID": "42"}))

    group0 = app.handlers[0]
    assert len(group0) == 8  # status/radar/recent/mute/unmute/test/help/start
    assert all(isinstance(h, CommandHandler) for h in group0)
    group1 = app.handlers[1]
    assert len(group1) == 1 and isinstance(group1[0], MessageHandler)


async def test_run_test_sends_alert_and_all_clear():
    config = {
        "TELEGRAM_TOKEN": "123:abc",
        "TELEGRAM_CHAT_ID": "42",
        "CWB_TOKEN": "w",
        "AREAS": [{"name": "測試區", "box": [23.76, 23.73, 120.58, 120.65]}],
    }
    sent = []

    class FakeSender:
        def __init__(self, bot, chat_id, max_retries=1):
            pass

        async def send_alert(self, text, img_path=None, buttons=None, chat_id=None):
            sent.append(("alert", text, chat_id))
            return True

        async def send_text(self, text, buttons=None, chat_id=None):
            sent.append(("text", text))
            return True

    class FakeBot:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    with patch("app.main.Bot", return_value=FakeBot()), \
         patch("app.main.TelegramSender", FakeSender), \
         patch("services.bot_commands.radar.download_radar", side_effect=RuntimeError("no net")):
        await run_test(config)

    kinds = [entry[0] for entry in sent]
    assert kinds == ["alert", "text"]
    assert "測試" in sent[0][1]
    assert sent[0][2] is None  # CLI --test has no originating chat -> push target
    assert sent[1][1].startswith("<b>✅ 雷擊警報解除</b>")


def test_command_menu_covers_all_public_commands():
    from app.main import COMMAND_MENU

    names = [name for name, _ in COMMAND_MENU]
    assert names == ["status", "radar", "recent", "mute", "unmute", "test", "help"]
    assert all(desc for _, desc in COMMAND_MENU)


async def test_register_command_menu_publishes_bot_commands():
    from telegram import BotCommand

    from app.main import COMMAND_MENU, register_command_menu

    app = SimpleNamespace(bot=AsyncMock())
    await register_command_menu(app)
    (cmds,) = app.bot.set_my_commands.call_args.args
    assert [c.command for c in cmds] == [name for name, _ in COMMAND_MENU]
    assert all(isinstance(c, BotCommand) for c in cmds)


def test_redact_secrets_scrubs_bot_and_cwa_tokens():
    from app.main import _redact_secrets

    record = {
        "message": (
            "HTTP Request: POST https://api.telegram.org/bot8628379071:"
            'AAE9XmppwEv6mZLrgJVTVSXjUj4Ofj1jJH4/getUpdates "200 OK" and '
            "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/O-A0039-001"
            "?Authorization=CWA-12345678-ABCD&downloadType=WEB"
        )
    }
    _redact_secrets(record)
    assert "AAE9" not in record["message"]
    assert "CWA-12345678" not in record["message"]
    assert "bot<redacted>/getUpdates" in record["message"]
    assert "Authorization=<redacted>&downloadType" in record["message"]


def test_configure_logging_redacts_tokens_and_caps_http_noise(tmp_path):
    from app.main import configure_logging

    log_file = tmp_path / "probe.log"
    configure_logging(str(log_file))
    try:
        logging.getLogger("probe.request").warning(
            "HTTP Request: POST https://api.telegram.org/bot123456:%s/getMe", "A" * 35
        )
        assert logging.getLogger("httpx").level == logging.WARNING
        assert logging.getLogger("httpcore").level == logging.WARNING
        assert logging.getLogger("telegram").level == logging.INFO
    finally:
        logger.remove()
        logger.add(sys.stderr)
    content = log_file.read_text()
    assert "bot<redacted>/getMe" in content
    assert "A" * 35 not in content


def test_intercept_handler_routes_stdlib_logging_to_loguru():
    # The headline reliability fix: infrastructure modules log via stdlib `logging`,
    # and the InterceptHandler must route those records into loguru's sinks.
    captured = []
    sink_id = logger.add(captured.append, format="{message}", level="DEBUG")
    probe = logging.getLogger("infrastructure.bridge_probe")
    probe.handlers = [InterceptHandler()]
    probe.setLevel(logging.DEBUG)
    probe.propagate = False
    try:
        probe.warning("bridge probe %s", "ok")
    finally:
        logger.remove(sink_id)
    assert any("bridge probe ok" in line for line in captured)
