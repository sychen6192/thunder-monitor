---
name: Telegram Bot Redesign
description: Telegram-only 常駐 bot — 圖文合一彙整推播、互動指令、座標欄位修正、雷達圖放大
type: refactor
---

# Thunder Monitor — Telegram Bot 重構設計

## 1. 概述

現況是 cron 驅動的一次性批次：每輪抓 CWA 落雷資料 → 過濾 → 對 Telegram + LINE 推播，一筆警報發兩則訊息（文字、圖片分開）。本次重構改為**單一常駐 Telegram bot 程序**，並把通知體驗整個翻新：

- 通知通道只留 Telegram，刪除 LINE、Imgur 及其抽象層（`Notifier` ABC、`NotificationManager`）
- 推播改為 `sendPhoto` + HTML caption 圖文合一——一次警戒只響一次；同輪多筆落雷彙整成一則摘要
- 新增互動指令：`/status`、`/radar`、`/recent`、`/mute`、`/unmute`、`/test`、`/help`
- 修正 `Alert` 座標欄位對調的歷史問題（repo 文件中已知的 open question）
- 雷達圖裁切範圍放大並升採樣，手機上可讀
- 保留 `--once` 執行模式：跑一輪就退出、不啟動 bot（cron / Lambda 相容逃生門）

## 2. 目標

- 一次警戒事件 = 一則推播通知，不論該輪有幾筆落雷
- 使用者可隨時主動查詢狀態（`/status`）、即時雷達（`/radar`）、近期記錄（`/recent`）
- 雷雨轟炸時可暫時靜音（`/mute`），且靜音不遺失狀態記錄
- 座標在程式內名實相符，顯示一律「(緯度, 經度)」標準順序
- 訊息文字仍集中於 `message_format`，可用固定 `now` 做 snapshot 測試

## 3. 非目標

- Webhook 模式——先用 long polling（自架最簡單），之後要換再說
- 多使用者 / 訂閱管理——維持單一 `TELEGRAM_CHAT_ID`
- 歷史資料庫——state 僅輕量 JSON + 24 小時 ring buffer
- 由 AREAS 自動幾何推導雷達裁切框——需對 CWA 底圖做地理校準，列為日後延伸
- 雷達圖上畫落雷標記——同上，依賴同一套校準

## 4. 架構

```
                   ┌────────────────────────────────────┐
                   │ app/main.py（常駐程序）              │
                   │ python-telegram-bot Application     │
                   │                                    │
  每 60s ─────────▶│ JobQueue: monitor job              │
                   │   └─ services/monitor.run_once()   │
  /status 等 ─────▶│ CommandHandlers（chat_id 白名單）    │
                   │   └─ services/bot_commands         │
                   └───────────────┬────────────────────┘
                                   │
                ┌──────────────────┼───────────────────┐
                ▼                  ▼                   ▼
          cwb_client          state_repo             radar
          （CWA 落雷 KMZ）    （state.json：警戒/     （雷達裁圖，
                              靜音/歷史/上次檢查）      放大版）
```

- 依賴方向維持 `app → services → domain → models`，`infrastructure` 提供 I/O，`domain` 保持純邏輯不變。
- **執行模式**：
  - `python app/main.py --env PROD` → 常駐（bot 指令 + JobQueue 排程監測）
  - `python app/main.py --once [--env ...]` → 跑一輪監測即退出，不啟動 bot。給不想跑常駐程序的人留的 cron 相容路徑（無互動指令）。
  - `--test` 保留：發合成測試警報後退出（同現行，預設 STAGE）。

## 5. 元件設計

### 5.1 `models/alert.py` + `domain/alert_checker.py` — 座標欄位正名（bug 修正）

CWA description 的「經緯度: 120.2 , 22.6」實際順序是**經度在前**（經緯度＝經度、緯度；台灣經度 ~120、緯度 ~22）。現行 `_parse_alert` 把 120.2 存進 `latitude` 欄位，下游靠 `_in_areas`（拿 latitude 跟 left/right 經度界比）和 `get_google_url`（參數再反轉一次）兩次互換「碰巧」正確；訊息顯示端沒有反轉，輸出「位置：120.2, 22.6」＝經緯顛倒的非標準順序。

修正：

```python
# _parse_alert：對齊 CWA 實際順序
long_str, lat_str = coord_match.group(1).strip().split(" , ")
return Alert(category, occur_time, latitude=float(lat_str), longitude=float(long_str))
```

- `_in_areas` 改為名實相符的 `down <= lat <= top and left <= long <= right`。AREAS 的 `[top, down, left, right]` 語意不變，**使用者設定檔不需要改**。
- `get_google_url(lat, long)` → `?q={lat},{long}`。地圖連結最終結果與現行相同（原本就是雙重互換後碰巧正確），此處只是讓程式可讀。
- 顯示一律「(22.6, 120.2)」＝ (緯度, 經度)。
- `tests/fixtures/sample_thunder.kml` 不用改（它本來就是 CWA 真實順序），但相關斷言更新。
- 舊 `alert.txt` state 因欄位語意改變直接作廢，不做遷移（見 5.4）。

### 5.2 `services/monitor.py` — 監測邏輯（取代 `alert_service.py`）

```python
async def run_once(deps) -> CheckResult
```

1. `state_repo` 載入 state
2. 抓 CWA → `is_alert_valid` 過濾（domain 不變）
3. 與 `active_alerts` diff 出 `new_alerts`
4. 有新落雷 → 下載雷達圖 → 發**一則** digest 訊息（見 6.1）
5. 全部清空且先前有警戒 → 發解除訊息（見 6.3）
6. 更新 state：`active_alerts`、24h `history`、`last_check`
7. 回傳 `CheckResult(time, ok, new_count, error)`——`/status` 直接引用

**靜音規則**：`muted_until` 未過期 → 第 4、5 步跳過發送，但 state 照常更新（記錄不遺失）；靜音結束後不補發舊警報，從下一輪自然恢復。解除訊息在靜音期間同樣不發——靜音就是全靜音。

### 5.3 `infrastructure/telegram.py` — 發送層（取代 `telegram_notifier.py`）

- 用 python-telegram-bot 的 async API：`bot.send_photo(chat_id, photo, caption=..., parse_mode=HTML, reply_markup=InlineKeyboardMarkup(...))`
- 失敗重試 1 次（沿用現行 `max_retries` 精神，簡單 for 迴圈即可）
- 雷達圖下載或上傳失敗 → **降級為純文字** `send_message`，警報不因圖片中斷
- `Notifier` ABC 與 `NotificationManager` 廢除——單通道不需要抽象層

### 5.4 `infrastructure/state_repo.py` — 狀態儲存（取代 `file_repo.py` / `alert.txt`）

`state.json`：

```json
{
  "active_alerts": [ {"category": "...", "occur_time": "...", "latitude": 22.6, "longitude": 120.2} ],
  "muted_until": "2026-07-18T16:35:00+08:00",
  "last_check": {"time": "2026-07-18T16:04:32+08:00", "ok": true, "new_count": 3, "error": null},
  "history": [ {"...同 Alert...": "近 24h，上限 200 筆，供 /recent"} ]
}
```

- 壞檔 / 缺欄位 → 重置為空 state + warning log（沿用現行 file_repo「壞檔不能卡死之後每一輪」的原則）
- 舊 `alert.txt` 不遷移：座標語意已變，且 dedup 視窗僅 15 分鐘，重置成本近零。啟動時若偵測到舊檔，log 提示可刪除。

### 5.5 `infrastructure/radar.py` — 雷達圖（取代 `image_processor.py`）

- 現行裁切框 `(415, 520, 510, 630)` 只有 95×110 px。改為**同中心約 3 倍範圍**裁切，再 LANCZOS 2× 升採樣，輸出約 570×660，手機上可辨識回波位置
- 時間戳字級加大、加白色描邊，避免融進回波色塊
- 實作時以一張實際下載的 `lightning_s.jpg` 目視校驗裁切範圍涵蓋監測區

### 5.6 `infrastructure/config.py`

| key | 必填 | 說明 |
|---|---|---|
| `TELEGRAM_TOKEN` | ✔ | bot token |
| `TELEGRAM_CHAT_ID` | ✔ | 推播對象；同時是指令白名單 |
| `CWB_TOKEN` | ✔ | CWA OpenData token |
| `LOG` | ✔ | log 路徑 |
| `AREAS` | ✔ | 監測區，支援命名（見下） |
| `POLL_INTERVAL_SECONDS` | ✖ | 監測間隔，預設 60 |
| `DEBUG` | ✖ | 同現行 |

- **刪除**：`LINE_CHANNEL_ACCESS_TOKEN`、`LINE_TO`、`IMGUR_CLIENT_ID`（含驗證邏輯與 example 模板）
- **AREAS 升級為可命名**，訊息裡顯示「高雄」而不是裸座標：

```yaml
AREAS:
  - name: 高雄
    box: [22.65694, 22.598, 120.158, 120.3025]   # [top, down, left, right]
```

仍相容舊的裸 list 形式（`- [22.65, 22.59, 120.15, 120.30]`），無名時顯示「區域 1」。

### 5.7 `app/main.py`

- 組裝 `Application`、註冊 CommandHandlers、`job_queue.run_repeating(monitor_job, interval=POLL_INTERVAL_SECONDS, first=0)`
- **白名單守衛**：非 `TELEGRAM_CHAT_ID` 來的更新一律靜默忽略 + log（不回覆，避免向陌生人暴露 bot 用途）
- loguru `InterceptHandler` 保留（PTB 內部 stdlib logging 一樣會被收進 LOG sink）
- `--once` / `--test`：不建 Application，直接跑對應流程後退出

## 6. 訊息格式定稿（exact）

所有格式仍集中在 `message_format.py`，`now` 可注入，snapshot 測試鎖定精確字串。以下粗體以 HTML `<b>` 實作。

### 6.1 落雷警報（同輪多筆彙整為一則，photo + caption）

```
⚡ 雷擊警報 — 高雄
新增 3 筆落雷 · 最近一筆 15:47（約 2 分鐘前）

• 15:47 雲對地（22.63, 120.29）
• 15:45 雲對雲（22.61, 120.27）
• 15:44 雲對地（22.60, 120.30）
```

- 首行粗體；跨多區時標題列出所有涉及區名（「高雄、台南」）
- 超過 5 筆列最近 5 筆，末行加「…另有 N 筆」
- Inline 按鈕：`[📍 開啟地圖]`（最近一筆座標的 Google Maps）`[🌩 CWA 雷達頁]`（官網即時雷達）

### 6.2 單筆時的簡化形

```
⚡ 雷擊警報 — 高雄
15:47（約 2 分鐘前）· 雲對地
位置 (22.63, 120.29)
```

按鈕同 6.1。

### 6.3 警報解除

```
✅ 雷擊警報解除
解除 16:08 · 本次警戒約 21 分鐘（共 5 筆）
```

- 「共 N 筆」= 本次警戒期間 history 累計筆數（比現行只講最早一筆更有資訊量）
- 相對時間規則沿用現行：`剛剛` / `約 N 分鐘前` / `約 N 小時前`

### 6.4 互動指令

| 指令 | 行為 |
|---|---|
| `/status` | 警戒狀態、上次檢查時間與結果、監測區、靜音狀態 |
| `/radar` | 當下即時抓一張雷達裁圖傳回 |
| `/recent` | 近 24 小時落雷：各區統計 + 最近 10 筆列表 |
| `/mute [分鐘]` | 靜音 N 分鐘（預設 30，上限 720）|
| `/unmute` | 立即解除靜音 |
| `/test` | 發一筆合成測試警報，走完整 digest 格式（取代 CLI `--test` 的日常用途）|
| `/help` | 指令說明 |

`/status` 回覆示意：

```
📊 Thunder Monitor
警戒：無活動落雷 ✅
上次檢查：16:04:32（成功）
監測區：高雄、台南
通知：開啟
```

- 警戒中 → `警戒：⚡ 3 筆活動落雷（最近 15:47）`
- 靜音中 → `通知：🔇 靜音至 16:35`
- 上次檢查失敗 → `上次檢查：16:04:32（失敗：<簡短錯誤>）`

`/mute 30` 回覆：`🔇 已靜音至 16:35。期間落雷照常記錄但不推播，/unmute 可提前恢復。`

## 7. 相依套件

- **新增**：`python-telegram-bot[job-queue]`（實作時鎖定當時最新穩定版；`[job-queue]` extra 帶入 APScheduler 供排程用）、`pytest-asyncio`（測 async 流程）
- **移除**：無——`requests`、`lxml`、`Pillow`、`PyYAML`、`loguru`、`cssselect` 全部續用（CWA 抓取與解析路徑不動）

## 8. 檔案異動清單

**刪除（含測試共 9 檔）**

- `infrastructure/line_notifier.py`、`infrastructure/imgur_client.py`
- `infrastructure/notifier.py`（ABC）、`infrastructure/notification_manager.py`
- `tests/unit/test_line_notifier.py`、`test_imgur_client.py`、`test_notifier.py`、`test_notification_manager.py`
- `alert.txt`（state 改用 `state.json`，加入 `.gitignore`）

**取代重寫（含對應測試檔）**

- `services/alert_service.py` → `services/monitor.py`（async、digest、靜音、CheckResult）；`test_alert_service.py` → `test_monitor.py`
- `infrastructure/telegram_notifier.py` → `infrastructure/telegram.py`（async、photo+caption、按鈕、降級）；`test_telegram_notifier.py` → `test_telegram.py`
- `infrastructure/file_repo.py` → `infrastructure/state_repo.py`（單一 JSON state）；`test_file_repo.py` → `test_state_repo.py`
- `infrastructure/image_processor.py` → `infrastructure/radar.py`（放大裁切）

**新增**

- `services/bot_commands.py`（指令邏輯：薄 handler + 純函數產文字）
- `tests/unit/test_bot_commands.py`、`test_radar.py`

**修改**

- `models/alert.py`、`domain/alert_checker.py`（座標正名，5.1）
- `infrastructure/message_format.py`（digest / 解除 / status 等格式，第 6 節）
- `infrastructure/config.py`（key 增刪、AREAS 命名、POLL_INTERVAL）
- `app/main.py`（PTB 組裝、`--once`、白名單）
- `config.example.yaml`、`README.md`、`CLAUDE.md`、`requirements.txt`
- `tests/unit/test_alert_checker.py`、`test_message_format.py`、`test_config.py`、`test_config_example.py`、`test_main.py`（隨上述更新）

## 9. 測試策略

1. **純函數層（不需網路、不需 bot）**：`message_format` 以固定 `now` 做 snapshot（digest 多筆 / 單筆 / 解除 / 超過 5 筆截斷）；`alert_checker` 用既有 KML fixture 驗證座標正名後 in-area 判斷；`/status`、`/recent` 的回覆文字抽成 `status_text(state)`、`recent_text(state)` 純函數直接斷言。
2. **state_repo**：round-trip、壞檔重置、history 24h/200 筆修剪、muted_until 過期判斷。
3. **monitor.run_once**（mock cwb / telegram / radar）：多筆只發一則、無新落雷不發、清空發解除、靜音跳過發送但 state 有更新、圖片失敗降級純文字。
4. **指令 handler**：邏輯集中在純函數，handler 只做組裝；白名單守衛用假 Update 驗證陌生 chat_id 被忽略（pytest-asyncio）。
5. **真機驗證（STAGE）**：跑常駐 → `/test` 看 digest 渲染與按鈕 → `/mute` + `/status` + `/unmute` 互動流程 → `/radar` 確認新裁切圖大小可讀。

依 repo 慣例採 spec → plan → 每任務一 commit、測試先行。

## 10. 部署變更（重要）

加入互動指令後，程式**從 cron 批次變成常駐程序**——這是本次唯一的部署面變更：

- **常駐（預設）**：systemd 範例

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

（Docker 亦可，`restart: always` 同理。）

- **不想常駐**：`--once` + cron 照舊運作，行為等同重構前（但無互動指令、無 `/mute`）。
- Lambda 形態僅適用 `--once` 路徑。
- 原 cron 排程記得移除，避免與常駐程序重複推播（兩者共用 state.json 會互踩）。

## 11. 風險與備註

- **座標正名是行為變更**：地圖連結結果不變（原本雙重互換後就是對的），但訊息顯示順序改為標準 (lat, long)，且舊 `alert.txt` 作廢。風險低、一次付清。
- **PTB 為 asyncio 架構**：`services`/`infrastructure` 發送側改 async；`domain`、`models`、解析與格式化維持同步純函數，測試負擔不變。
- **輪詢頻率**：`POLL_INTERVAL_SECONDS` 預設 60，與現行 cron 每分鐘一次對齊；CWA 資料本身約每分鐘更新。
- **repo 內附的 `venv/` shebang 已壞**（CLAUDE.md 記載）：重構落地時建議直接重建 venv 並更新 CLAUDE.md 的指令說明。
- 日後延伸（本次不做）：雷達圖地理校準（自動裁切框 + 落雷標記）、webhook 模式、多訂閱者。

