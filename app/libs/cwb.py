from PIL import Image, ImageDraw
import requests
from io import BytesIO
import datetime
from zipfile import ZipFile
from lxml import html
from urllib.request import urlopen
from app.libs.utils import read_config

def download_thunder_img(output):
    try:
        res = requests.get("https://www.cwa.gov.tw/Data/lightning/lightning_s.jpg")
        if res.status_code == 200:
            img = Image.open(BytesIO(res.content))
            crop_img = img.crop((415, 520, 510, 630))
            draw_obj = ImageDraw.Draw(crop_img)
            timestamp = datetime.datetime.now().strftime("%H:%M")
            draw_obj.text((1, 100), timestamp, fill='black')
            crop_img.save(output)
    except Exception as err:
        raise Exception(err)

def get_thunder_data(token):
    resp = urlopen(f"https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/O-A0039-001?Authorization={token}&downloadType=WEB&format=KMZ")
    kmz = ZipFile(BytesIO(resp.read()))
    kml = kmz.open('doc.kml', 'r').read()
    doc = html.fromstring(kml)
    return doc
    
if __name__ == "__main__":
    a = read_config()
    env = "PROD"
    res = get_thunder_data(a[env]["CWB_TOKEN"])
