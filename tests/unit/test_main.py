import sys
from unittest.mock import Mock, patch

from app.main import parse_args, send_test_notifications


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


def test_parse_args_default_is_prod_run():
    with patch.object(sys, "argv", ["main.py"]):
        args = parse_args()
    assert args.test is False
    assert args.env == "PROD"


def test_send_test_notifications_sends_alert_and_clearance():
    service = Mock()
    with patch("app.main.image_processor.download_thunder_img"):
        send_test_notifications(service)
    assert service.notifier.send_all.called
    assert service.notifier.send_message_all.called
    sent_alert = service.notifier.send_all.call_args[0][0]
    assert "測試" in sent_alert.category
