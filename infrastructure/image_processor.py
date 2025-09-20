import requests
from PIL import Image, ImageDraw
from io import BytesIO
import datetime


def download_thunder_img(output_path: str):
    res = requests.get("https://www.cwa.gov.tw/Data/lightning/lightning_s.jpg")
    res.raise_for_status()
    with Image.open(BytesIO(res.content)) as img:
        crop = img.crop((415, 520, 510, 630))
        draw = ImageDraw.Draw(crop)
        timestamp = datetime.datetime.now().strftime("%H:%M")
        draw.text((1, 100), timestamp, fill="black")
        crop.save(output_path)
