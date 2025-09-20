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

```yaml
STAGE:
  TELEGRAM_TOKEN: "<your_bot_token>"
  TELEGRAM_CHAT_ID: "<chat_id>"
  CWB_TOKEN: "<cwa_open_data_token>"
  LOG: "log/thunder.log"
```

---

## 🚀 How to Run

1. Install dependencies
   pip install -r requirements.txt

2. Run the app
   python app/main.py
