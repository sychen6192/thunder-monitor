import requests
import datetime
import yaml

def read_config(file_path="config.yaml", env="PROD"):
    with open(file_path, "r") as f:
        return yaml.safe_load(f)[env]
    
def check_areas(areas, longitude, latitude):
    for area in areas:
        top, down, left, right = area
        if left <= float(latitude) <= right:
            if down <= float(longitude) <= top:
                return True
    return False

def get_google_url(long, lat):
    return f"https://www.google.com/maps?q={str(long)},{str(lat)}"

def send_line_notify(msg, token, img_path=None):
    headers = {"Authorization": "Bearer " + token}
    payload = {'message': f'\n{msg}'}
    files = None
    if img_path:
        files = {'imageFile': open(img_path, 'rb')}
    r = requests.post("https://notify-api.line.me/api/notify", headers=headers, params=payload, files=files)
    return r.status_code

def diff_time(occur_time):
    nowTime = datetime.datetime.now()
    startTime = datetime.datetime.strptime(occur_time, '%Y-%m-%d %H:%M')
    diff_sec = (nowTime - startTime).seconds
    return diff_sec

if __name__ == "__main__":
    send_line_notify("only text", "neKt05luYWhJgVIisCe8KrZ6fFO9ktDPGObd8e6QM6L")