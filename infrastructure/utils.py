from datetime import datetime
from zoneinfo import ZoneInfo 

def get_google_url(long, lat):
    return f"https://www.google.com/maps?q={long},{lat}"

def diff_time(occur_time: str) -> int:
    tw_zone = ZoneInfo("Asia/Taipei")
    now = datetime.now(tz=tw_zone)
    start = datetime.strptime(occur_time, '%Y-%m-%d %H:%M')
    start = start.replace(tzinfo=tw_zone)
    return int((now - start).total_seconds())
