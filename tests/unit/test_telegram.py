from unittest.mock import AsyncMock

from telegram import InlineKeyboardMarkup
from telegram.constants import ParseMode

from infrastructure.telegram import TelegramSender


def _sender(bot) -> TelegramSender:
    return TelegramSender(bot, chat_id="c", max_retries=1)


async def test_send_text_success():
    bot = AsyncMock()
    assert await _sender(bot).send_text("hi") is True
    kwargs = bot.send_message.call_args.kwargs
    assert kwargs["chat_id"] == "c"
    assert kwargs["text"] == "hi"
    assert kwargs["parse_mode"] == ParseMode.HTML
    assert kwargs["reply_markup"] is None


async def test_send_text_retries_then_fails():
    bot = AsyncMock()
    bot.send_message.side_effect = Exception("boom")
    assert await _sender(bot).send_text("hi") is False
    assert bot.send_message.call_count == 2  # max_retries=1 -> two attempts


async def test_send_text_recovers_on_retry():
    bot = AsyncMock()
    bot.send_message.side_effect = [Exception("boom"), None]
    assert await _sender(bot).send_text("hi") is True
    assert bot.send_message.call_count == 2


async def test_send_alert_sends_photo_with_caption_and_buttons(tmp_path):
    img = tmp_path / "crop.jpg"
    img.write_bytes(b"jpg")
    bot = AsyncMock()
    ok = await _sender(bot).send_alert(
        "<b>alert</b>", img_path=str(img), buttons=[("📍 開啟地圖", "https://maps.example")]
    )
    assert ok is True
    bot.send_message.assert_not_called()
    kwargs = bot.send_photo.call_args.kwargs
    assert kwargs["caption"] == "<b>alert</b>"
    assert kwargs["parse_mode"] == ParseMode.HTML
    markup = kwargs["reply_markup"]
    assert isinstance(markup, InlineKeyboardMarkup)
    assert markup.inline_keyboard[0][0].url == "https://maps.example"


async def test_send_alert_falls_back_to_text_when_photo_fails(tmp_path):
    img = tmp_path / "crop.jpg"
    img.write_bytes(b"jpg")
    bot = AsyncMock()
    bot.send_photo.side_effect = Exception("boom")
    ok = await _sender(bot).send_alert("alert", img_path=str(img))
    assert ok is True
    assert bot.send_photo.call_count == 2  # retried before falling back
    bot.send_message.assert_called_once()


async def test_send_alert_without_image_is_text():
    bot = AsyncMock()
    assert await _sender(bot).send_alert("alert") is True
    bot.send_photo.assert_not_called()
    bot.send_message.assert_called_once()
