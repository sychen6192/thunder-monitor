import datetime

def get_google_url(long, lat):
    return f"https://www.google.com/maps?q={long},{lat}"


def diff_time(occur_time):
    now = datetime.datetime.now()
    start = datetime.datetime.strptime(occur_time, "%Y-%m-%d %H:%M")
    return int((now - start).total_seconds())