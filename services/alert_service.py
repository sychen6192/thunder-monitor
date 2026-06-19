from typing import Any

from loguru import logger

from domain.alert_checker import is_alert_valid
from infrastructure import cwb_client, image_processor, file_repo
from infrastructure.telegram_notifier import TelegramNotifier
from infrastructure.line_notifier import LineNotifier
from infrastructure.imgur_client import ImgurClient
from infrastructure.notification_manager import NotificationManager
from infrastructure.message_format import format_clearance


class AlertService:
    def __init__(self, config: dict[str, Any]) -> None:
        self.areas = config["AREAS"]
        self.token = config["CWB_TOKEN"]

        imgur_client = None
        if config.get("IMGUR_CLIENT_ID"):
            imgur_client = ImgurClient(config["IMGUR_CLIENT_ID"])

        notifiers = [TelegramNotifier(config["TELEGRAM_TOKEN"], config["TELEGRAM_CHAT_ID"])]
        if config.get("LINE_CHANNEL_ACCESS_TOKEN") and config.get("LINE_TO"):
            notifiers.append(
                LineNotifier(
                    config["LINE_CHANNEL_ACCESS_TOKEN"],
                    config["LINE_TO"],
                    imgur_client=imgur_client,
                )
            )
        self.notifier = NotificationManager(notifiers)

    def run(self):
        prev_alerts = file_repo.load_alerts()
        doc = cwb_client.get_thunder_data(self.token)
        current_alerts = is_alert_valid(doc, self.areas)

        new_alerts = [a for a in current_alerts if a not in prev_alerts]

        if new_alerts:
            image_processor.download_thunder_img("crop.jpg")
            for alert in new_alerts:
                results = self.notifier.send_all(alert, "crop.jpg")
                logger.info("delivery {} -> {}", alert.occur_time, results)
            file_repo.save_alerts(current_alerts)
        elif not current_alerts and prev_alerts:
            file_repo.reset_alerts()
            image_processor.download_thunder_img("crop.jpg")
            earliest = min(a.occur_time for a in prev_alerts)
            results = self.notifier.send_message_all(
                format_clearance(earliest_occur_time=earliest), "crop.jpg"
            )
            logger.info("clearance delivery -> {}", results)
