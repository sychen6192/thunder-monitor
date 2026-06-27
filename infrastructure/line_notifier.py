import json
import logging

import requests

from infrastructure.notifier import Notifier
from infrastructure.imgur_client import ImgurClient

logger = logging.getLogger(__name__)

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


class LineNotifier(Notifier):
    def __init__(
        self,
        channel_access_token: str,
        to: str,
        imgur_client: ImgurClient | None = None,
    ):
        self.channel_access_token = channel_access_token
        self.to = to
        self.imgur_client = imgur_client

    def send_message(self, message: str, img_path: str | None = None) -> bool:
        messages = [{"type": "text", "text": message}]

        if img_path and self.imgur_client:
            url = self.imgur_client.upload_image(img_path)
            if url:
                messages.append({
                    "type": "image",
                    "originalContentUrl": url,
                    "previewImageUrl": url,
                })
            else:
                logger.warning("Imgur upload failed; sending LINE text-only")

        try:
            resp = requests.post(
                LINE_PUSH_URL,
                headers={
                    "Authorization": f"Bearer {self.channel_access_token}",
                    "Content-Type": "application/json",
                },
                data=json.dumps({"to": self.to, "messages": messages}),
                timeout=10,
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"LINE notification failed: {e}")
            return False
