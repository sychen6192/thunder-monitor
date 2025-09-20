from domain.alert_checker import is_alert_valid
from infrastructure import (
cwb_client,
image_processor,
file_repo,
telegram_notifier,
)
from typing import Any


class AlertService:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.areas = config["AREAS"]
        self.token = config["CWB_TOKEN"]
        self.notifier = telegram_notifier.TelegramNotifier(config["TELEGRAM_TOKEN"], config["TELEGRAM_CHAT_ID"])

    def run(self):
        prev_alerts = file_repo.load_alerts()
        doc = cwb_client.get_thunder_data(self.token)
        current_alerts = is_alert_valid(doc, self.areas)

        new_alerts = [a for a in current_alerts if a not in prev_alerts]

        if new_alerts:
            image_processor.download_thunder_img("crop.jpg")
            for alert in new_alerts:
                self.notifier.send(alert, "crop.jpg")
            file_repo.save_alerts(current_alerts)
        elif not current_alerts and prev_alerts:
            file_repo.reset_alerts()
            image_processor.download_thunder_img("crop.jpg")
            self.notifier.send_message("⚠️ 雷擊警報解除", "crop.jpg")
