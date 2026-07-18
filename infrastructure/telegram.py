"""Async Telegram delivery: photo+caption with inline buttons, text fallback, retry.

Replaces the Notifier ABC / NotificationManager / TelegramNotifier stack —
with a single channel there is nothing left to fan out.
"""

import logging
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)

Buttons = Optional[list[tuple[str, str]]]


def _markup(buttons: Buttons) -> Optional[InlineKeyboardMarkup]:
    if not buttons:
        return None
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, url=url) for text, url in buttons]])


class TelegramSender:
    """Sends ready-made Telegram-HTML strings to the configured chat.

    ``bot`` is any object exposing PTB's async ``send_message``/``send_photo``.
    Every send gets up to ``max_retries`` extra attempts; a photo message that
    keeps failing falls back to text-only so an alert never dies with its image.
    """

    def __init__(self, bot, chat_id: str, max_retries: int = 1):
        self.bot = bot
        self.chat_id = chat_id
        self.max_retries = max_retries

    async def send_alert(self, text: str, img_path: Optional[str] = None, buttons: Buttons = None) -> bool:
        if img_path:
            if await self._attempt(self._send_photo, text, img_path, _markup(buttons)):
                return True
            logger.error("Photo send failed after retries; falling back to text-only alert")
        return await self.send_text(text, buttons)

    async def send_text(self, text: str, buttons: Buttons = None) -> bool:
        return await self._attempt(self._send_message, text, _markup(buttons))

    async def _send_message(self, text: str, markup) -> None:
        await self.bot.send_message(
            chat_id=self.chat_id, text=text, parse_mode=ParseMode.HTML, reply_markup=markup
        )

    async def _send_photo(self, caption: str, img_path: str, markup) -> None:
        with open(img_path, "rb") as photo:
            await self.bot.send_photo(
                chat_id=self.chat_id,
                photo=photo,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=markup,
            )

    async def _attempt(self, fn, *args) -> bool:
        for attempt in range(self.max_retries + 1):
            try:
                await fn(*args)
                return True
            except Exception as e:
                logger.error(f"Telegram send failed (attempt {attempt + 1}): {e}")
        return False
