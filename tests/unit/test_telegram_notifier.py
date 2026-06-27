from unittest.mock import patch
from infrastructure.telegram_notifier import TelegramNotifier
from infrastructure.notifier import Notifier


def test_telegram_notifier_implements_notifier():
    assert issubclass(TelegramNotifier, Notifier)


def test_send_message_success_returns_true():
    with patch("infrastructure.telegram_notifier.requests.post") as mock_post:
        mock_post.return_value.raise_for_status.return_value = None
        notifier = TelegramNotifier("token", "chat")
        assert notifier.send_message("hi") is True
        mock_post.assert_called_once()


def test_send_message_failure_returns_false():
    with patch("infrastructure.telegram_notifier.requests.post") as mock_post:
        mock_post.side_effect = Exception("boom")
        notifier = TelegramNotifier("token", "chat")
        assert notifier.send_message("hi") is False
