"""Radar snapshot: download CWA's lightning radar image, crop the region, upscale.

Replaces ``image_processor``. The old crop was a 95x110 px box — unreadable on a
phone. Same center, triple the span, upscaled 2x, with a legible timestamp.
"""

import datetime
import logging
from io import BytesIO
from zoneinfo import ZoneInfo

import requests
from PIL import Image, ImageDraw, ImageFont

RADAR_URL = "https://www.cwa.gov.tw/Data/lightning/lightning_s.jpg"

# Old box: (415, 520, 510, 630), center (462.5, 575). Tripled span, same center.
CROP_BOX = (320, 410, 605, 740)
UPSCALE = 2
TW = ZoneInfo("Asia/Taipei")

logger = logging.getLogger(__name__)


def download_radar(output_path: str = "crop.jpg") -> str:
    """Fetch the CWA radar image, crop + upscale + timestamp it, save to ``output_path``."""
    res = requests.get(RADAR_URL, timeout=15)
    res.raise_for_status()
    with Image.open(BytesIO(res.content)) as img:
        left, top, right, bottom = CROP_BOX
        right, bottom = min(right, img.width), min(bottom, img.height)
        left, top = max(0, min(left, right - 1)), max(0, min(top, bottom - 1))
        crop = img.crop((left, top, right, bottom))
        crop = crop.resize((crop.width * UPSCALE, crop.height * UPSCALE), Image.LANCZOS)
        _stamp_time(crop)
        crop.save(output_path)
    return output_path


def _stamp_time(img: Image.Image) -> None:
    draw = ImageDraw.Draw(img)
    timestamp = datetime.datetime.now(TW).strftime("%H:%M")
    try:
        font = ImageFont.load_default(size=28)
    except TypeError:  # Pillow < 10.1 without size support
        font = ImageFont.load_default()
    draw.text(
        (10, img.height - 42),
        timestamp,
        fill="black",
        font=font,
        stroke_width=3,
        stroke_fill="white",
    )
