from lxml import html
from zipfile import ZipFile
from urllib.request import urlopen
from io import BytesIO


def get_thunder_data(token):
    url = f"https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/O-A0039-001?Authorization={token}&downloadType=WEB&format=KMZ"
    with urlopen(url) as resp:
        kmz = ZipFile(BytesIO(resp.read()))
        kml = kmz.open("doc.kml").read()
        return html.fromstring(kml)
