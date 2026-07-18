from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from infrastructure.radar import download_radar


def _fake_response(width: int, height: int) -> Mock:
    buf = BytesIO()
    Image.new("RGB", (width, height), "white").save(buf, format="JPEG")
    resp = Mock()
    resp.content = buf.getvalue()
    resp.raise_for_status.return_value = None
    return resp


def test_download_radar_crops_and_upscales(tmp_path):
    out = tmp_path / "crop.jpg"
    with patch("infrastructure.radar.requests.get", return_value=_fake_response(620, 760)):
        download_radar(str(out))
    with Image.open(out) as img:
        # box (320, 410, 605, 740) -> 285x330, upscaled 2x
        assert img.size == (570, 660)


def test_download_radar_clamps_small_source(tmp_path):
    out = tmp_path / "crop.jpg"
    with patch("infrastructure.radar.requests.get", return_value=_fake_response(500, 600)):
        download_radar(str(out))
    with Image.open(out) as img:
        # box clamped to (320, 410, 500, 600) -> 180x190, upscaled 2x
        assert img.size == (360, 380)


def test_download_radar_propagates_http_error(tmp_path):
    resp = Mock()
    resp.raise_for_status.side_effect = RuntimeError("503")
    with patch("infrastructure.radar.requests.get", return_value=resp):
        with pytest.raises(RuntimeError):
            download_radar(str(tmp_path / "crop.jpg"))
