import logging

import requests

from models.alert import Alert
from infrastructure.notifier import Notifier
from infrastructure.message_format import format_alert

logger = logging.getLogger(__name__)


class TelegramNotifier(Notifier):
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id

    def send(self, alert: Alert, img_path: str | None = None) -> bool:
        return self.send_message(format_alert(alert), img_path)

    def send_message(self, message: str, img_path: str | None = None) -> bool:
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                data={"chat_id": self.chat_id, "text": message},
                timeout=10,
            )
            resp.raise_for_status()

            if img_path:
                with open(img_path, "rb") as photo:
                    resp = requests.post(
                        f"https://api.telegram.org/bot{self.token}/sendPhoto",
                        data={"chat_id": self.chat_id},
                        files={"photo": photo},
                        timeout=10,
                    )
                resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")
            return False
