# ⚡ Thunder Alert Monitor

This is a Python-based lightning alert system that fetches real-time lightning strike data from the Central Weather Administration (CWA) of Taiwan, filters it by geolocation and time, and sends alerts via Telegram with a cropped radar image.

## 📦 Features

- Realtime lightning data ingestion from CWA OpenData
- Region-based filtering (multiple areas supported)
- Recent-only alert filtering (default: last 15 minutes)
- Sends alert messages with image to Telegram
- Alert deduplication via local file
- Lambda-compatible architecture

---

## 🗺️ Alert Message Format

Example alert sent to Telegram:
Time: 2025-09-20 15:47
Type: Cloud-to-ground
Coordinates: (23.769, 120.587)
https://www.google.com/maps?q=120.587,23.769

---

## ⚙️ Configuration (`config.yaml`)

Copy `config.example.yaml` to `config.yaml` and fill in your credentials. There are two
environments (`PROD` / `STAGE`); each needs `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`,
`LINE_CHANNEL_ACCESS_TOKEN`, `LINE_TO`, `CWB_TOKEN`, `LOG`, and `AREAS`
(`IMGUR_CLIENT_ID` is optional). See `config.example.yaml` for the full template.

---

## 🚀 How to Run

1. Install dependencies
   `./venv/bin/python -m pip install -r requirements.txt`

2. Create your config from the template and fill in credentials
   `cp config.example.yaml config.yaml` then edit `config.yaml`
   (`config.yaml` is gitignored. `IMGUR_CLIENT_ID` is optional — without it, LINE sends text-only.)

3. Send a test notification without waiting for real lightning (goes to STAGE)
   `./venv/bin/python app/main.py --test`

4. Run for real
   `./venv/bin/python app/main.py --env PROD`

## 🔔 Notifications

Alerts are pushed to Telegram, and also to LINE when LINE is configured (leave the LINE keys blank in `config.yaml` for a Telegram-only setup). LINE images are hosted via Imgur (HTTPS required by LINE).
Run the test suite with `./venv/bin/python -m pytest`.
