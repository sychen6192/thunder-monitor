import requests
import textwrap

from models.alert import Alert
from infrastructure.utils import get_google_url

class TelegramNotifier:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id

    def send(self, alert: Alert, img_path=None):
        msg = textwrap.dedent(f"""\
        時間：{alert.occur_time}
        類型：{alert.category}
        經緯度：({alert.latitude}, {alert.longitude})
        {get_google_url(alert.longitude, alert.latitude)}
        """)
        self.send_message(msg, img_path)

    def send_message(self, msg, img_path=None):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        data = {"chat_id": self.chat_id, "text": msg}
        requests.post(url, data=data)

        if img_path:
            url = f"https://api.telegram.org/bot{self.token}/sendPhoto"
            with open(img_path, "rb") as photo:
                requests.post(url, data={"chat_id": self.chat_id}, files={"photo": photo})
