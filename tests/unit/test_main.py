import logging
import sys
from unittest.mock import AsyncMock, patch

from loguru import logger
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from app.main import InterceptHandler, allowed_chat_filter, parse_args, register_handlers, run_test
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


def test_allowed_chat_filter_numeric_id():
    f = allowed_chat_filter({"TELEGRAM_CHAT_ID": "-1001234"})
    assert isinstance(f, filters.Chat)
    assert -1001234 in f.chat_ids


def test_allowed_chat_filter_username_fallback():
    f = allowed_chat_filter({"TELEGRAM_CHAT_ID": "@mychannel"})
    assert isinstance(f, filters.Chat)
    assert "mychannel" in f.usernames


def test_register_handlers_whitelists_commands_and_logs_strangers():
    app = Application.builder().token("123:abc").build()
    commands = Commands(
        {"AREAS": [{"name": "x", "box": [1.0, 0.0, 0.0, 1.0]}]},
        sender=AsyncMock(),
        lock=None,
    )
    register_handlers(app, commands, allowed_chat_filter({"TELEGRAM_CHAT_ID": "42"}))

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

        async def send_alert(self, text, img_path=None, buttons=None):
            sent.append(("alert", text))
            return True

        async def send_text(self, text, buttons=None):
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

    kinds = [k for k, _ in sent]
    assert kinds == ["alert", "text"]
    assert "測試" in sent[0][1]
    assert sent[1][1].startswith("<b>✅ 雷擊警報解除</b>")


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
