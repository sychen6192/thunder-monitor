from io import BytesIO
from zipfile import ZipFile

from lxml import html

from infrastructure.cwa_http import fetch_bytes


def get_thunder_data(token):
    url = f"https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/O-A0039-001?Authorization={token}&downloadType=WEB&format=KMZ"
    kmz = ZipFile(BytesIO(fetch_bytes(url)))
    kml = kmz.open("doc.kml").read()
    return html.fromstring(kml)
