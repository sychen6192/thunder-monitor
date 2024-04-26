# -*- coding: UTF-8 -*-
import re
import time
import os
from loguru import logger
from app.libs.utils import check_areas, read_config, diff_time, send_line_notify, get_google_url
from app.libs.cwb import get_thunder_data, download_thunder_img

ENV_VAR = read_config(env="STAGE")
logger.add(ENV_VAR["LOG"], rotation="1 week")
areas = [[22.65694, 22.598, 120.158, 120.3025], [22.58, 22.52, 120.177, 120.349]]

def main():
    try:
        if os.path.isfile("alert.txt"):
            with open('alert.txt') as f: prev_alert_list = f.read().splitlines()
        else:
            prev_alert_list = []
        alert_list = []
        doc = get_thunder_data(ENV_VAR["CWB_TOKEN"])
        for pm in doc.cssselect('Document Folder Placemark'):
            des = pm.cssselect('description')[0].text_content()
            category = re.search(r"閃電種類:(.*)", des).group(1).strip()
            occur_time = re.search(r"時間:(.*)", des).group(1).strip()
            latitude, longitude = re.search(r"經緯度: (.*)", des).group(1).strip().split(' , ')
            if (diff_time(occur_time)) <= 900:
                if check_areas(areas, longitude, latitude):
                    record = f"{category},{occur_time},{latitude},{longitude}"
                    alert_list.append(record)      

        for i, item in enumerate(set(alert_list) - set(prev_alert_list)):
            if i == 0:
                download_thunder_img("crop.jpg")
            category, occur_time, latitude, longitude= item.split(',')
            message = f'時間： {occur_time}\n類型： {category}\n經緯度：({str(latitude)},{str(longitude)})\n{get_google_url(longitude, latitude)}'
            send_line_notify(message, ENV_VAR["LINE_TOKEN"], "crop.jpg")
            with open('alert.txt', 'a+') as f: f.writelines(item+'\n')
            logger.error(item)

        if not alert_list and prev_alert_list:
            with open('alert.txt', 'w') as f: f.writelines('')
            download_thunder_img("crop.jpg")
            send_line_notify("雷擊警報解除", ENV_VAR["LINE_TOKEN"], "crop.jpg")
            logger.success('雷擊警報解除')
    except Exception as err:
        send_line_notify(f"Error occur: {err}", ENV_VAR["LINE_TOKEN"])

if __name__ == "__main__":
    main()