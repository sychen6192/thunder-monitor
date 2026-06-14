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


def test_send_formats_alert_and_delegates(sample_alert):
    with patch.object(TelegramNotifier, "send_message", return_value=True) as mock_send:
        notifier = TelegramNotifier("token", "chat")
        assert notifier.send(sample_alert) is True
        mock_send.assert_called_once()
        sent_text = mock_send.call_args[0][0]
        assert sample_alert.occur_time in sent_text
        assert sample_alert.category in sent_text
