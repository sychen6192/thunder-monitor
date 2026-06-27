import logging
import sys
from unittest.mock import Mock, patch

from loguru import logger

from app.main import InterceptHandler, parse_args, send_test_notifications


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
    assert service.notifier.send_message_all.call_count == 2
    first_message = service.notifier.send_message_all.call_args_list[0].args[0]
    assert "測試" in first_message


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
