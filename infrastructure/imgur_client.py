import logging

import requests

logger = logging.getLogger(__name__)

IMGUR_UPLOAD_URL = "https://api.imgur.com/3/image"


class ImgurClient:
    def __init__(self, client_id: str):
        self.client_id = client_id

    def upload_image(self, image_path: str) -> str | None:
        try:
            with open(image_path, "rb") as image_file:
                resp = requests.post(
                    IMGUR_UPLOAD_URL,
                    headers={"Authorization": f"Client-ID {self.client_id}"},
                    files={"image": image_file},
                    timeout=10,
                )
            resp.raise_for_status()
            return resp.json()["data"]["link"]
        except Exception as e:
            logger.error(f"Imgur upload failed: {e}")
            return None
