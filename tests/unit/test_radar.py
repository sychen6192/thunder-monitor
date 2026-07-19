from io import BytesIO
from unittest.mock import patch

import pytest
from PIL import Image

from infrastructure.radar import download_radar


def _fake_jpeg(width: int, height: int) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (width, height), "white").save(buf, format="JPEG")
    return buf.getvalue()


def test_download_radar_crops_and_upscales(tmp_path):
    out = tmp_path / "crop.jpg"
    with patch("infrastructure.radar.fetch_bytes", return_value=_fake_jpeg(620, 760)):
        download_radar(str(out))
    with Image.open(out) as img:
        # box (320, 410, 605, 740) -> 285x330, upscaled 2x
        assert img.size == (570, 660)


def test_download_radar_clamps_small_source(tmp_path):
    out = tmp_path / "crop.jpg"
    with patch("infrastructure.radar.fetch_bytes", return_value=_fake_jpeg(500, 600)):
        download_radar(str(out))
    with Image.open(out) as img:
        # box clamped to (320, 410, 500, 600) -> 180x190, upscaled 2x
        assert img.size == (360, 380)


def test_download_radar_propagates_fetch_error(tmp_path):
    with patch("infrastructure.radar.fetch_bytes", side_effect=RuntimeError("503")):
        with pytest.raises(RuntimeError):
            download_radar(str(tmp_path / "crop.jpg"))
