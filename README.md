# ⚡ Thunder Alert Monitor

A Telegram bot that watches real-time lightning-strike data from Taiwan's
Central Weather Administration (CWA), filters strikes by your configured
areas, and pushes **one digest notification per detection round** — with an
interactive side: query status, pull the latest radar image, or mute it while
a storm hammers your phone.

## 📦 Features

- Long-running Telegram bot — a built-in scheduler runs a detection round every 60s (configurable)
- One notification per round: multiple new strikes collapse into a single photo + caption digest
- Named watch areas — alerts and `/recent` label strikes by area name (e.g. 高雄)
- Interactive commands: `/status` `/radar` `/recent` `/mute` `/unmute` `/test` `/help`
- Episode-aware all-clear message with duration and total strike count
- Inline buttons: open the strike on Google Maps, jump to CWA's live lightning page
- Commands whitelisted to your chat id; anyone else is silently ignored (and logged)
- `--once` mode: single detection round, no bot — cron / Lambda-compatible

## 🗺️ Alert Message

Sent as a radar photo with an HTML caption and buttons:

```
⚡ 雷擊警報 — 高雄
新增 3 筆落雷 · 最近一筆 15:47（約 2 分鐘前）

• 15:47 雲對地（22.63, 120.29）
• 15:45 雲對雲（22.61, 120.27）
• 15:44 雲對地（22.6, 120.3）

[📍 開啟地圖] [🌩 CWA 雷達頁]
```

When the last strike leaves the 15-minute window:

```
✅ 雷擊警報解除
解除 16:08 · 本次警戒約 21 分鐘（共 5 筆）
```

## ⚙️ Configuration (`config.yaml`)

Copy `config.example.yaml` to `config.yaml` and fill in your credentials
(`config.yaml` is gitignored — never commit real tokens). Two environments
(`PROD` / `STAGE`) with these keys each:

| key | required | notes |
|---|---|---|
| `TELEGRAM_TOKEN` | ✔ | bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | ✔ | push target **and** command whitelist |
| `CWB_TOKEN` | ✔ | CWA OpenData token |
| `LOG` | ✔ | log file path |
| `AREAS` | ✔ | list of named boxes: `- name: 高雄` / `box: [top, down, left, right]` (lat N, lat S, long W, long E); legacy bare `[t, d, l, r]` entries still work |
| `POLL_INTERVAL_SECONDS` | – | detection interval for daemon mode, default 60 |

## 🚀 Run

1. Install dependencies (Python 3.11+)
   `python3 -m venv venv && ./venv/bin/pip install -r requirements.txt`

2. Create your config
   `cp config.example.yaml config.yaml` and fill in credentials

3. See what the messages look like without waiting for real lightning (goes to STAGE)
   `./venv/bin/python app/main.py --test`

4. Run the bot
   `./venv/bin/python app/main.py --env PROD`

The bot is a long-running process. A minimal systemd unit:

```ini
[Unit]
Description=Thunder Monitor Telegram Bot
After=network-online.target

[Service]
WorkingDirectory=/path/to/thunder-monitor
ExecStart=/path/to/thunder-monitor/venv/bin/python app/main.py --env PROD
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Prefer cron / Lambda instead? `./venv/bin/python app/main.py --once` runs a
single detection round and exits (no interactive commands in this mode).
Don't run the daemon and a cron schedule at the same time — they would fight
over `state.json` and double-notify.

## 🔔 Commands

| command | what it does |
|---|---|
| `/status` | current alert state, last check result, watch areas, mute state |
| `/radar` | fetch the latest radar crop right now |
| `/recent` | last-24h strikes: per-area counts + newest 10 |
| `/mute [min]` | mute notifications (default 30, max 720) — strikes are still recorded |
| `/unmute` | resume notifications |
| `/test` | push a clearly-marked synthetic alert through the real pipeline |
| `/help` | command list (also `/start`) |

## 🧪 Tests

`./venv/bin/python -m pytest`
