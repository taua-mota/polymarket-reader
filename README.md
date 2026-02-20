# Polymarket Position Monitor

A bot that watches one or more Polymarket user profiles and sends a Telegram alert whenever they open, increase, or close a position.

---

## How it works

Every 30 seconds (configurable) the bot:

1. Reads the monitored user list from `config.json`
2. Fetches each user's current positions from the Polymarket Data API
3. Diffs against the last-known snapshot stored in `data/state.json`
4. Sends a Telegram message for every new or changed position
5. Saves the updated snapshot

On first run all existing positions are silently loaded as a baseline — no notification flood.

---

## Quick start

### Prerequisites

- Python 3.11+
- A Telegram bot token ([create one via @BotFather](https://t.me/BotFather))
- The chat ID you want alerts sent to
- PowerShell with [Invoke-Build](https://github.com/nightroman/Invoke-Build) (`Install-Module InvokeBuild -Scope CurrentUser`)

### Setup

```powershell
# 1. Install dependencies into a local venv
Invoke-Build Install

# 2. Create your .env from the template
Copy-Item .env.example .env
# Edit .env and fill in TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

# 3. Edit config.json to set the users you want to monitor (see below)

# 4. Start the bot
Invoke-Build        # default task = Run
```

---

## Configuration

### `.env` (secrets — never commit this)

```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF-your-token-here
TELEGRAM_CHAT_ID=-1001234567890
```

### `config.json`

```json
{
  "polling_interval_seconds": 30,
  "monitored_users": [
    {
      "username": "Pedro-Messi",
      "profile_url": "https://polymarket.com/profile/@Pedro-Messi",
      "wallet_address": "0xdd9ed02bb67b2ec504be24b98febd651fdac49b3"
    }
  ],
  "notifications": {
    "on_new_position": true,
    "on_position_increase": true,
    "on_position_closed": false
  },
  "first_run_suppress_notifications": true,
  "authorized_chat_ids": []
}
```

| Field | Description |
|---|---|
| `wallet_address` | Optional. Skip API resolution if you already know it. Leave blank to auto-resolve from the username. |
| `on_new_position` | Alert when a brand-new position appears. |
| `on_position_increase` | Alert when shares on an existing position grow by more than 0.5. |
| `on_position_closed` | Alert when a position disappears entirely. |
| `first_run_suppress_notifications` | Silently baseline all existing positions on first start. |

> The bot hot-reloads `config.json` every poll cycle. Add or remove users without restarting.

---

## Invoke-Build tasks

| Command | What it does |
|---|---|
| `Invoke-Build` | Start the bot (default) |
| `Invoke-Build Run` | Start the bot |
| `Invoke-Build Test` | Run the test suite (24 tests) |
| `Invoke-Build TestStrict` | Tests with deprecation warnings as errors |
| `Invoke-Build Install` | Create venv + install all dependencies |
| `Invoke-Build Clean` | Remove `state.json`, `__pycache__`, `.pytest_cache` |
| `Invoke-Build Reset` | Clean + full reinstall |

---

## Telegram messages

### Bot online / offline

```
🟢 Polymarket Monitor is online

Polling every 30s for 1 user(s):

👤 Pedro-Messi
   0xdd9ed02bb67b2ec504be24b98febd651fdac49b3
```

```
🔴 Polymarket Monitor is offline
```

### New position alert

```
🟢 New Position Detected

👤 Pedro-Messi
📊 Will Oscar Piastri be the 2026 F1 Drivers' Champion?

Side: ✅ Yes @ 7¢
Shares: 8,583.2
Value: $514.99

🔗 https://polymarket.com/event/2026-f1-drivers-champion/will-oscar-piastri-...
```

### Position increased alert

```
📈 Position Increased

👤 Pedro-Messi
📊 Will George Russell be the 2026 F1 Drivers' Champion?

Side: ❌ No @ 69¢
Shares: 999.8 → 1,999.8 (+1,000.0)
Value: $1,399.89

🔗 https://polymarket.com/event/...
```

---

## State persistence

Positions are stored on disk in `data/state.json` (gitignored). The file is read and written on every poll cycle, so the bot survives restarts without re-notifying on known positions.

---

## Project layout

```
polymarket-reader/
├── .env.example               # Credentials template
├── .build.ps1                 # Invoke-Build tasks
├── config.json                # Users + settings
├── requirements.txt
├── src/
│   ├── main.py                # Scheduler entry point
│   ├── config.py              # Config loader
│   ├── models.py              # Position, ChangeEvent dataclasses
│   ├── agents/
│   │   ├── profile_resolver.py
│   │   ├── position_poller.py
│   │   ├── change_detector.py
│   │   ├── telegram_notifier.py
│   │   └── state_manager.py
│   └── utils/
│       ├── http_client.py     # Async HTTP with retry + rate-limit handling
│       └── logger.py
├── data/state.json            # Runtime state (gitignored)
└── tests/                     # 24 unit tests
```

See [AGENTS.md](AGENTS.md) for detailed component descriptions and [MASTER_PLAN.md](MASTER_PLAN.md) for the full roadmap.
