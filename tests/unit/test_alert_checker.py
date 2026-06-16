from pathlib import Path
from unittest.mock import patch

from lxml import html

from domain.alert_checker import is_alert_valid

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_thunder.kml"

# AREAS are [top, down, left, right]; _in_areas checks left<=lat<=right and down<=long<=top.
# The fixture stores coordinates as "經緯度: <first> , <second>" -> Alert(latitude=first, longitude=second).
AREAS = [[22.66, 22.59, 120.15, 120.31]]


def _doc():
    return html.fromstring(FIXTURE.read_bytes())


def test_is_alert_valid_keeps_in_area_recent():
    with patch("domain.alert_checker.diff_time", return_value=100):  # within 900s
        alerts = is_alert_valid(_doc(), AREAS)
    assert len(alerts) == 1
    assert alerts[0].category == "雲對地"
    assert alerts[0].latitude == 120.2
    assert alerts[0].longitude == 22.6


def test_is_alert_valid_drops_stale():
    # all placemarks are stale here, so recency (not the area filter) empties the result
    with patch("domain.alert_checker.diff_time", return_value=5000):  # older than 900s
        alerts = is_alert_valid(_doc(), AREAS)
    assert alerts == []
