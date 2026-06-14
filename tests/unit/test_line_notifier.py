import json
from unittest.mock import Mock, patch

from infrastructure.line_notifier import LineNotifier
from infrastructure.notifier import Notifier


def test_line_notifier_implements_notifier():
    assert issubclass(LineNotifier, Notifier)


def test_send_message_text_only_success():
    with patch("infrastructure.line_notifier.requests.post") as mock_post:
        mock_post.return_value.raise_for_status.return_value = None
        notifier = LineNotifier("token", "U123", imgur_client=None)
        assert notifier.send_message("hello") is True
        payload = json.loads(mock_post.call_args[1]["data"])
        assert payload["to"] == "U123"
        assert len(payload["messages"]) == 1
        assert payload["messages"][0]["type"] == "text"


def test_send_with_image_appends_image_message():
    imgur = Mock()
    imgur.upload_image.return_value = "https://i.imgur.com/x.jpg"
    with patch("infrastructure.line_notifier.requests.post") as mock_post:
        mock_post.return_value.raise_for_status.return_value = None
        notifier = LineNotifier("token", "U123", imgur_client=imgur)
        assert notifier.send_message("hi", "crop.jpg") is True
        imgur.upload_image.assert_called_once_with("crop.jpg")
        payload = json.loads(mock_post.call_args[1]["data"])
        assert len(payload["messages"]) == 2
        assert payload["messages"][1]["type"] == "image"
        assert payload["messages"][1]["originalContentUrl"] == "https://i.imgur.com/x.jpg"


def test_send_with_image_falls_back_to_text_when_imgur_fails():
    imgur = Mock()
    imgur.upload_image.return_value = None
    with patch("infrastructure.line_notifier.requests.post") as mock_post:
        mock_post.return_value.raise_for_status.return_value = None
        notifier = LineNotifier("token", "U123", imgur_client=imgur)
        assert notifier.send_message("hi", "crop.jpg") is True
        payload = json.loads(mock_post.call_args[1]["data"])
        assert len(payload["messages"]) == 1
        assert payload["messages"][0]["type"] == "text"


def test_send_formats_alert(sample_alert):
    with patch("infrastructure.line_notifier.requests.post") as mock_post:
        mock_post.return_value.raise_for_status.return_value = None
        notifier = LineNotifier("token", "U123")
        assert notifier.send(sample_alert) is True
        payload = json.loads(mock_post.call_args[1]["data"])
        text = payload["messages"][0]["text"]
        assert sample_alert.category in text
        assert sample_alert.occur_time in text
        assert "雷擊警報" in text


def test_send_message_api_failure_returns_false():
    with patch("infrastructure.line_notifier.requests.post") as mock_post:
        mock_post.side_effect = Exception("boom")
        notifier = LineNotifier("token", "U123")
        assert notifier.send_message("hi") is False
