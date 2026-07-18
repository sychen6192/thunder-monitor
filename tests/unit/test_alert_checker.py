from pathlib import Path
from unittest.mock import patch

from lxml import html

from domain.alert_checker import area_name_of, is_alert_valid

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_thunder.kml"

# AREAS come config-normalized: box = [top, down, left, right] = [lat N, lat S, long W, long E].
# The fixture stores coordinates in CWA order "經緯度: <經度 long> , <緯度 lat>".
AREAS = [{"name": "測試區", "box": [22.66, 22.59, 120.15, 120.31]}]


def _doc():
    return html.fromstring(FIXTURE.read_bytes())


def test_is_alert_valid_keeps_in_area_recent():
    with patch("domain.alert_checker.diff_time", return_value=100):  # within 900s
        alerts = is_alert_valid(_doc(), AREAS)
    assert len(alerts) == 1
    assert alerts[0].category == "雲對地"
    assert alerts[0].latitude == 22.6
    assert alerts[0].longitude == 120.2


def test_is_alert_valid_drops_stale():
    # all placemarks are stale here, so recency (not the area filter) empties the result
    with patch("domain.alert_checker.diff_time", return_value=5000):  # older than 900s
        alerts = is_alert_valid(_doc(), AREAS)
    assert alerts == []


def test_area_name_of_resolves_containing_area():
    assert area_name_of(22.6, 120.2, AREAS) == "測試區"


def test_area_name_of_returns_none_outside():
    assert area_name_of(30.0, 130.0, AREAS) is None
