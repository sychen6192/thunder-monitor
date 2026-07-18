"""Entry point.

Default: long-running Telegram bot — a JobQueue runs a detection round every
POLL_INTERVAL_SECONDS while command handlers serve /status, /radar, /recent,
/mute, /unmute, /test and /help (whitelisted to TELEGRAM_CHAT_ID).

``--once``: single detection round, no bot — cron/Lambda-compatible.
``--test``: one synthetic alert + all-clear pair to the configured chat, then exit.
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# Make `python app/main.py` work without packaging: put the repo root on sys.path
# so `infrastructure`/`services`/`domain`/`models` import as top-level packages.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from infrastructure.config import load_config
from infrastructure.message_format import format_all_clear
from infrastructure.telegram import TelegramSender
from services.bot_commands import Commands
from services.monitor import Monitor

TW = ZoneInfo("Asia/Taipei")


class InterceptHandler(logging.Handler):
    """Route stdlib logging records into loguru so infrastructure logs reach the LOG sink."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        # Walk back to the real caller so loguru's {name}:{function}:{line} fields
        # point at the infrastructure call site, not the stdlib logging internals.
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def main() -> None:
    args = parse_args()
    try:
        config = load_config(env=args.env)
        logger.add(config["LOG"], rotation="1 week")
        logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
        if args.test:
            asyncio.run(run_test(config))
        elif args.once:
            asyncio.run(run_single_round(config))
        else:
            run_daemon(config)
    except Exception as e:
        logger.exception(e)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Thunder Monitor")
    parser.add_argument("--env", default=None, choices=["PROD", "STAGE"], help="Environment config")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single detection round and exit — no bot, cron-compatible",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Send synthetic test notifications instead of monitoring (defaults to STAGE)",
    )
    args = parser.parse_args()
    if args.env is None:
        args.env = "STAGE" if args.test else "PROD"
    return args


def build_services(config: dict, bot) -> tuple[Monitor, Commands]:
    """Monitor and Commands share one sender and one state lock."""
    sender = TelegramSender(bot, config["TELEGRAM_CHAT_ID"])
    lock = asyncio.Lock()
    return Monitor(config, sender, lock), Commands(config, sender, lock)


def allowed_chat_filter(config: dict) -> filters.BaseFilter:
    """Whitelist filter for the configured chat: numeric id, or @username fallback."""
    raw = str(config["TELEGRAM_CHAT_ID"]).strip()
    try:
        return filters.Chat(chat_id=int(raw))
    except ValueError:
        return filters.Chat(username=raw.lstrip("@"))


def register_handlers(app: Application, commands: Commands, allowed: filters.BaseFilter) -> None:
    for name, callback in (
        ("status", commands.status),
        ("radar", commands.radar),
        ("recent", commands.recent),
        ("mute", commands.mute),
        ("unmute", commands.unmute),
        ("test", commands.test),
        ("help", commands.help),
        ("start", commands.help),  # Telegram convention: /start greets with the help text
    ):
        app.add_handler(CommandHandler(name, callback, filters=allowed))
    # Anything from outside the whitelist is silently ignored, with a log trail.
    app.add_handler(MessageHandler(~allowed, log_unauthorized), group=1)


async def log_unauthorized(update, context) -> None:
    chat = update.effective_chat
    logger.warning("Ignored update from unauthorized chat {}", chat.id if chat else "?")


def run_daemon(config: dict) -> None:
    app = Application.builder().token(config["TELEGRAM_TOKEN"]).build()
    monitor, commands = build_services(config, app.bot)
    register_handlers(app, commands, allowed_chat_filter(config))

    async def monitor_job(context) -> None:
        await monitor.run_once()

    interval = config["POLL_INTERVAL_SECONDS"]
    app.job_queue.run_repeating(monitor_job, interval=interval, first=1)
    logger.info("Daemon starting: detection round every {}s", interval)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


async def run_single_round(config: dict) -> None:
    async with Bot(config["TELEGRAM_TOKEN"]) as bot:
        monitor, _ = build_services(config, bot)
        result = await monitor.run_once()
        logger.info(
            "Single round done: ok={} new={} error={}", result.ok, result.new_count, result.error
        )


async def run_test(config: dict) -> None:
    """Synthetic alert + all-clear pair for visual inspection on a real device."""
    async with Bot(config["TELEGRAM_TOKEN"]) as bot:
        _, commands = build_services(config, bot)
        await commands.test(update=None, context=None)  # uses the sender, not the update
        occur = (datetime.now(TW) - timedelta(minutes=3)).strftime("%Y-%m-%d %H:%M")
        delivered = await commands.sender.send_text(format_all_clear(occur, 1))
        logger.info("Test all-clear delivery -> {}", delivered)


if __name__ == "__main__":
    main()
