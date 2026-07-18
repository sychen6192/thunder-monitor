"""Interactive Telegram commands.

Handlers stay thin: reply text comes from ``message_format`` pure functions,
state I/O goes through ``state_repo``, and mute writes share the monitor's
asyncio lock so a running detection round can't clobber a fresh mute.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Union
from zoneinfo import ZoneInfo

from loguru import logger
from telegram.constants import ParseMode

from models.alert import Alert
from infrastructure import radar, state_repo
from infrastructure.message_format import (
    alert_buttons,
    format_digest,
    help_text,
    mute_ack_text,
    mute_usage_text,
    radar_caption,
    recent_text,
    status_text,
    unmute_ack_text,
)
from infrastructure.telegram import TelegramSender

TW = ZoneInfo("Asia/Taipei")
MUTE_DEFAULT_MINUTES = 30
MUTE_MAX_MINUTES = 720
RADAR_FAILED_TEXT = "🌩 雷達圖抓取失敗，稍後再試。"


def parse_mute_minutes(args: list[str]) -> Optional[int]:
    """``/mute [分鐘]`` -> minutes, or None when the argument is invalid."""
    if not args:
        return MUTE_DEFAULT_MINUTES
    try:
        minutes = int(args[0])
    except (ValueError, TypeError):
        return None
    if not 1 <= minutes <= MUTE_MAX_MINUTES:
        return None
    return minutes


class Commands:
    def __init__(
        self,
        config: dict[str, Any],
        sender: TelegramSender,
        lock: asyncio.Lock,
        state_path: Union[str, Path] = "state.json",
        radar_path: str = "crop.jpg",
    ):
        self.areas = config["AREAS"]
        self.sender = sender
        self.lock = lock
        self.state_path = state_path
        self.radar_path = radar_path

    async def status(self, update, context) -> None:
        state = state_repo.load_state(self.state_path)
        await self._reply(update, status_text(state, self.areas))

    async def recent(self, update, context) -> None:
        state = state_repo.load_state(self.state_path)
        state.prune_history()  # view-side prune; the monitor persists its own pruning
        await self._reply(update, recent_text(state, self.areas))

    async def radar(self, update, context) -> None:
        try:
            path = await asyncio.to_thread(radar.download_radar, self.radar_path)
        except Exception as e:
            logger.warning(f"/radar failed: {e}")
            await self._reply(update, RADAR_FAILED_TEXT)
            return
        with open(path, "rb") as photo:
            await update.effective_message.reply_photo(photo=photo, caption=radar_caption())

    async def mute(self, update, context) -> None:
        minutes = parse_mute_minutes(context.args)
        if minutes is None:
            await self._reply(update, mute_usage_text())
            return
        until = datetime.now(TW) + timedelta(minutes=minutes)
        async with self.lock:
            state = state_repo.load_state(self.state_path)
            state.muted_until = until
            state_repo.save_state(state, self.state_path)
        await self._reply(update, mute_ack_text(until))

    async def unmute(self, update, context) -> None:
        async with self.lock:
            state = state_repo.load_state(self.state_path)
            state.muted_until = None
            state_repo.save_state(state, self.state_path)
        await self._reply(update, unmute_ack_text())

    async def test(self, update, context) -> None:
        """Push a synthetic alert through the real digest pipeline (photo, buttons and all)."""
        alert = self._synthetic_alert()
        text = format_digest([alert], self.areas)
        img_path = None
        try:
            img_path = await asyncio.to_thread(radar.download_radar, self.radar_path)
        except Exception as e:
            logger.warning(f"/test radar image failed, sending text-only: {e}")
        delivered = await self.sender.send_alert(text, img_path=img_path, buttons=alert_buttons(alert))
        logger.info("Test alert delivery -> {}", delivered)

    async def help(self, update, context) -> None:
        await self._reply(update, help_text())

    def _synthetic_alert(self) -> Alert:
        """A clearly-marked test strike at the first configured area's center."""
        top, down, left, right = self.areas[0]["box"]
        occur = (datetime.now(TW) - timedelta(minutes=3)).strftime("%Y-%m-%d %H:%M")
        return Alert("雲對地（測試）", occur, round((top + down) / 2, 4), round((left + right) / 2, 4))

    async def _reply(self, update, text: str) -> None:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)
