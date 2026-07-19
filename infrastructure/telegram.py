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

    async def send_alert(
        self,
        text: str,
        img_path: Optional[str] = None,
        buttons: Buttons = None,
        chat_id=None,
    ) -> bool:
        """Send to the configured chat, or to ``chat_id`` when overridden."""
        target = self.chat_id if chat_id is None else chat_id
        if img_path:
            if await self._attempt(self._send_photo, target, text, img_path, _markup(buttons)):
                return True
            logger.error("Photo send failed after retries; falling back to text-only alert")
        return await self.send_text(text, buttons, chat_id=target)

    async def send_text(self, text: str, buttons: Buttons = None, chat_id=None) -> bool:
        target = self.chat_id if chat_id is None else chat_id
        return await self._attempt(self._send_message, target, text, _markup(buttons))

    async def _send_message(self, chat_id, text: str, markup) -> None:
        await self.bot.send_message(
            chat_id=chat_id, text=text, parse_mode=ParseMode.HTML, reply_markup=markup
        )

    async def _send_photo(self, chat_id, caption: str, img_path: str, markup) -> None:
        with open(img_path, "rb") as photo:
            await self.bot.send_photo(
                chat_id=chat_id,
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
