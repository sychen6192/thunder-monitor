import re
from domain.models import Alert
from infrastructure.utils import diff_time
from loguru import logger
from lxml.html import HtmlElement
from typing import List, Union


def is_alert_valid(doc: HtmlElement, areas: list[list[float]]) -> List[Alert]:
    alerts: List[Alert] = []
    for pm in doc.cssselect("Document Folder Placemark"):
        try:
            des = pm.cssselect("description")[0].text_content()
            alert = _parse_alert(des)
            if alert and diff_time(alert.occur_time) <= 900 and _in_areas(areas, alert.latitude, alert.longitude):
                alerts.append(alert)
        except Exception as e:
            logger.warning(f"ignored: {e}")
    return alerts

def _parse_alert(description: str) -> Union[Alert, None]:
    try:
        catg_match = re.search(r"閃電種類:(.*)", description)
        time_match = re.search(r"時間:(.*)", description)
        coord_match = re.search(r"經緯度: (.*)", description)

        if not (catg_match and time_match and coord_match):
            return None

        category = catg_match.group(1).strip()
        occur_time = time_match.group(1).strip()
        lat_str, long_str = coord_match.group(1).strip().split(" , ")
        return Alert(category, occur_time, float(lat_str), float(long_str))
    except Exception:
        logger.exception("Invalid alert format")
        return None

def _in_areas(areas, lat, long):
    for top, down, left, right in areas:
        if left <= lat <= right and down <= long <= top:
            return True
    return False