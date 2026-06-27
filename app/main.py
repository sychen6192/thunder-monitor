import argparse
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from loguru import logger

from services.alert_service import AlertService
from infrastructure.config import load_config
from infrastructure import image_processor
from infrastructure.message_format import format_alert, format_clearance
from models.alert import Alert


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
        service = AlertService(config)
        if args.test:
            send_test_notifications(service)
        else:
            service.run()
    except Exception as e:
        logger.exception(e)


def send_test_notifications(service: AlertService) -> None:
    occur = (datetime.now(ZoneInfo("Asia/Taipei")) - timedelta(minutes=3)).strftime("%Y-%m-%d %H:%M")
    alert = Alert("Cloud-to-ground (測試)", occur, 25.0, 121.5)
    try:
        image_processor.download_thunder_img("crop.jpg")
        img = "crop.jpg"
    except Exception as e:
        logger.warning(f"test image download failed, sending without image: {e}")
        img = None
    logger.info("test alert delivery -> {}", service.notifier.send_message_all(format_alert(alert), img))
    logger.info(
        "test clearance delivery -> {}",
        service.notifier.send_message_all(format_clearance(earliest_occur_time=occur), img),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Thunder Monitor")
    parser.add_argument("--env", default=None, choices=["PROD", "STAGE"], help="Environment config")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Send synthetic test notifications instead of fetching real data (defaults to STAGE)",
    )
    args = parser.parse_args()
    if args.env is None:
        args.env = "STAGE" if args.test else "PROD"
    return args


if __name__ == "__main__":
    main()
