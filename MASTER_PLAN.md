# Master Plan — Polymarket Position Monitor Bot

> **Goal:** Build a bot that monitors one or more Polymarket user profiles, detects when they open new positions, and sends a Telegram notification with full trade details.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [API Research Summary](#2-api-research-summary)
3. [Implementation Phases](#3-implementation-phases)
4. [Project Structure](#4-project-structure)
5. [Configuration Design](#5-configuration-design)
6. [Data Models](#6-data-models)
7. [Telegram Message Format](#7-telegram-message-format)
8. [Error Handling & Resilience](#8-error-handling--resilience)
9. [Deployment](#9-deployment)
10. [Future Enhancements](#10-future-enhancements)

---

## 1. Architecture Overview

The system is a **polling-based monitor** that runs on a configurable interval (default: 30s). It uses Polymarket's public APIs (no authentication required for reading positions) and the Telegram Bot API for notifications.

```
  ┌──────────────────────────────────────────────────────────────────┐
  │                        Scheduler Loop                            │
  │                     (every 30-60 seconds)                        │
  │                                                                  │
  │  ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────┐ │
  │  │  Resolve    │──▶│  Fetch     │──▶│  Detect    │──▶│ Notify │ │
  │  │  Profiles   │   │  Positions │   │  Changes   │   │ Telegram│ │
  │  └────────────┘   └────────────┘   └─────┬──────┘   └────────┘ │
  │                                           │                      │
  │                                    ┌──────▼──────┐               │
  │                                    │ Save State  │               │
  │                                    │ (JSON/SQLite)│              │
  │                                    └─────────────┘               │
  └──────────────────────────────────────────────────────────────────┘
```

See [AGENTS.md](AGENTS.md) for detailed agent/component descriptions.

---

## 2. API Research Summary

### Polymarket APIs (all public, no auth needed for reading)

| API           | Base URL                           | Purpose                                        |
| ------------- | ---------------------------------- | ---------------------------------------------- |
| **Gamma API** | `https://gamma-api.polymarket.com` | Markets, events, profiles, search              |
| **Data API**  | `https://data-api.polymarket.com`  | User positions, trades, activity               |
| **CLOB API**  | `https://clob.polymarket.com`      | Orderbook, pricing (not needed for monitoring) |

### Key Endpoints

| Endpoint                                  | Description                                  | Rate Limit    |
| ----------------------------------------- | -------------------------------------------- | ------------- |
| `GET gamma-api/public-search?q=@username` | Resolve username to profile + wallet address | 350 req/10s   |
| `GET data-api/positions?user={address}`   | Current active positions for a wallet        | 150 req/10s   |
| `GET data-api/activity?user={address}`    | Onchain activity feed for a wallet           | 1,000 req/10s |
| `GET gamma-api/markets/{id}`              | Market details (question, slug, outcomes)    | 300 req/10s   |

### Profile → Address Resolution

Polymarket profile URLs use `@username` but the Data API requires the user's **Polygon wallet address** (`0x...`). Two supported methods:

1. **Direct config** — set `wallet_address` in `config.json` for each user (preferred, zero API calls).
2. **Auto-resolve** — leave `wallet_address` blank and the bot queries `GET /public-search?q=<username>` on the Gamma API, then caches the result.

> **Note:** The Gamma API public-search endpoint requires the query parameter `q=` (not `query=`).

### Actual Position Data Shape (from Data API)

```json
{
  "proxyWallet": "0xdd9ed02bb67b2ec504be24b98febd651fdac49b3",
  "asset": "688274741289798174...",
  "conditionId": "0xe1d573...",
  "size": 51033.7347,
  "avgPrice": 0.0012,
  "initialValue": 61.4956,
  "currentValue": 76.5506,
  "cashPnl": 15.0549,
  "curPrice": 0.0015,
  "title": "Will Eduardo Bolsonaro win the 2026 Brazilian presidential election?",
  "slug": "will-eduardo-bolsonaro-win-the-2026-brazilian-presidential-election",
  "eventSlug": "brazil-presidential-election",
  "outcome": "Yes",
  "endDate": "2026-10-04"
}
```

---

## 3. Implementation Phases

### Phase 1 — Foundation (MVP) ✅ COMPLETE

> Get the core loop working end-to-end for a single user.

- [x] **1.1** Project scaffolding (folder structure, virtual environment, dependencies)
- [x] **1.2** Config loader — read `.env` (Telegram token, chat ID) + `config.json` (users list, poll interval)
- [x] **1.3** Profile Resolver — resolve `@username` → wallet address via Gamma API (with in-memory cache); skip if `wallet_address` pre-configured
- [x] **1.4** Position Poller — fetch positions from Data API for a given address
- [x] **1.5** State Manager — JSON file storage (`data/state.json`) for last-known positions
- [x] **1.6** Change Detector — diff current vs stored, emit new position events
- [x] **1.7** Telegram Notifier — send a formatted message for each new position; startup (🟢) and shutdown (🔴) messages
- [x] **1.8** Scheduler — `asyncio` loop tying it all together with hot-reload of `config.json`
- [x] **1.9** End-to-end test with real Polymarket profile `@Pedro-Messi` (49 positions loaded as baseline)

### Phase 2 — Multi-User, Commands & Robustness

> Scale to multiple users, add Telegram command management, and harden error handling.

- [x] **2.1** Multi-user support — loop over all configured profiles each cycle
- [x] **2.2** Graceful first-run — suppress notifications for all existing positions on startup
- [ ] **2.3** Telegram Command Handler — `/add @user`, `/remove @user`, `/list`, `/status`
- [ ] **2.4** Persist command changes to `config.json` so they survive restarts
- [ ] **2.5** Authorize commands — only respond to allowed chat IDs
- [x] **2.6** Error isolation — one user's failure doesn't crash the loop
- [x] **2.7** Retry logic — exponential backoff for API failures (3 attempts: 5s/15s/45s)
- [x] **2.8** Rate limit awareness — respect `Retry-After` header, back off automatically
- [x] **2.9** Structured logging with timestamps and user context

### Phase 3 — Enhanced Notifications

> Richer Telegram messages and more event types.

- [x] **3.1** Detect position increases (same market, more shares)
- [x] **3.2** Detect position closures (position disappeared)
- [x] **3.3** Rich Telegram messages with inline links and formatting
- [ ] **3.4** Optional: Telegram inline keyboard with link to market
- [ ] **3.5** Daily summary message (total positions, P&L overview)

### Phase 4 — Deployment & Operations

> Make it production-ready.

- [ ] **4.1** Dockerfile for containerized deployment
- [ ] **4.2** Docker Compose with restart policy
- [ ] **4.3** Health check endpoint (optional, simple HTTP)
- [ ] **4.4** Add/remove monitored users at runtime (config hot-reload or Telegram command)
- [x] **4.5** Documentation — README with setup guide

---

## 4. Project Structure

```
polymarket-reader/
├── AGENTS.md                  # Agent/component definitions
├── MASTER_PLAN.md             # This file
├── README.md                  # Setup & usage guide
├── .env.example               # Template for environment variables
├── .build.ps1                 # Invoke-Build tasks (Run, Test, Install, Clean)
├── config.json                # Monitored users + settings
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container build (Phase 4)
├── docker-compose.yml         # Container orchestration (Phase 4)
│
├── src/
│   ├── __init__.py
│   ├── main.py                # Entry point — starts the scheduler loop
│   ├── config.py              # Config loading (.env + config.json)
│   ├── models.py              # Data classes (Position, ChangeEvent, User)
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── profile_resolver.py    # @username → wallet address (cached)
│   │   ├── position_poller.py     # Fetch positions from Data API
│   │   ├── change_detector.py     # Diff engine
│   │   ├── telegram_notifier.py   # Telegram Bot API integration
│   │   ├── telegram_commands.py   # /add, /remove, /list, /status (Phase 2)
│   │   └── state_manager.py       # JSON file persistence
│   │
│   └── utils/
│       ├── __init__.py
│       ├── http_client.py     # Shared async HTTP client with retry/rate-limit
│       └── logger.py          # Logging configuration
│
├── data/
│   └── state.json             # Runtime state (gitignored)
│
├── scripts/
│   └── probe_profile.py       # Dev utility: explore Polymarket API responses
│
└── tests/
    ├── __init__.py
    ├── test_profile_resolver.py
    ├── test_change_detector.py
    └── test_telegram_notifier.py
```

---

## 5. Configuration Design

### `.env` (secrets — never committed)

```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=-1001234567890
```

### `config.json` (settings — can be committed)

This file serves as both the **initial seed** and the **persistent store**. Users added via Telegram commands are written back here so they survive restarts.

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

> **Tip:** `wallet_address` is optional. If omitted, the bot resolves it automatically via the Gamma API and caches the result.

### Adding Profiles (Two Methods)

**Method 1 — `config.json` (initial setup / bulk edits):**  
Edit the `monitored_users` array directly. The bot reads this file on startup and re-reads it each poll cycle.

**Method 2 — Telegram commands (runtime management):**  
Send commands to the bot from an authorized chat:

| Command                | Description                                |
| ---------------------- | ------------------------------------------ |
| `/add @Pedro-Messi`    | Start monitoring a new profile             |
| `/remove @Pedro-Messi` | Stop monitoring a profile                  |
| `/list`                | Show all monitored profiles                |
| `/status`              | Bot health: uptime, last poll, users count |

Changes made via Telegram are written back to `config.json` immediately.

---

## 6. Data Models

### `MonitoredUser`

```python
@dataclass
class MonitoredUser:
    username: str           # "Pedro-Messi"
    profile_url: str        # "https://polymarket.com/profile/@Pedro-Messi"
    wallet_address: str     # "0x..." (resolved at runtime)
```

### `Position`

```python
@dataclass
class Position:
    market_slug: str        # "will-oscar-piastri-be-the-2026-f1-drivers-champion"
    market_question: str    # "Will Oscar Piastri be the 2026 F1 Drivers' Champion?"
    token_id: str           # CLOB token ID
    side: str               # "Yes" or "No"
    size: float             # Number of shares (8583.2)
    avg_price: float        # Average entry price (0.07)
    current_price: float    # Current market price (0.06)
    value: float            # Current value in USD (514.99)
    event_slug: str         # "2026-f1-drivers-champion"
```

### `ChangeEvent`

```python
@dataclass
class ChangeEvent:
    event_type: str         # "new_position" | "position_increased" | "position_closed"
    user: MonitoredUser
    position: Position
    previous_size: float | None   # For increases, what it was before
    detected_at: datetime
```

---

## 7. Telegram Message Format

### New Position Alert

```
🟢 New Position Detected

👤 Pedro-Messi
📊 Will Oscar Piastri be the 2026 F1 Drivers' Champion?

Side: ✅ Yes @ 7¢
Shares: 8,583.2
Value: $514.99

🔗 https://polymarket.com/event/2026-f1-drivers-champion/will-oscar-piastri-be-the-2026-f1-drivers-champion
```

### Position Increase Alert (Phase 3)

```
📈 Position Increased

👤 Pedro-Messi
📊 Will George Russell be the 2026 F1 Drivers' Champion?

Side: ❌ No @ 69¢
Shares: 999.8 → 1,999.8 (+1,000.0)
Value: $1,399.89

🔗 https://polymarket.com/event/2026-f1-drivers-champion/will-george-russell-be-the-2026-f1-drivers-champion
```

---

## 8. Error Handling & Resilience

| Scenario                   | Strategy                                                                |
| -------------------------- | ----------------------------------------------------------------------- |
| Polymarket API down        | Retry with exponential backoff (3 attempts, 5s/15s/45s) then skip cycle |
| Telegram API down          | Queue messages, retry on next cycle                                     |
| Username can't be resolved | Log error, skip user, continue with others                              |
| Rate limit hit             | Respect `Retry-After` header, back off automatically                    |
| State file corrupt         | Fall back to empty state (suppress all notifs on next cycle)            |
| Network timeout            | 10s timeout per request, retry once                                     |
| First run                  | Load all current positions into state WITHOUT sending notifications     |

---

## 9. Deployment

### Local Development

```bash
python -m venv venv
source venv/bin/activate    # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env        # Fill in Telegram credentials
python -m src.main
```

### Docker (Phase 4)

```bash
docker compose up -d
docker compose logs -f
```

### Recommended Hosting Options

- **VPS** (DigitalOcean, Hetzner) — cheapest, most control
- **Railway / Render** — easy deploy from GitHub
- **Home server / Raspberry Pi** — free, always-on

---

## 10. Future Enhancements

| Feature                       | Description                                                                 | Priority |
| ----------------------------- | --------------------------------------------------------------------------- | -------- |
| **Telegram commands**         | `/add @user`, `/remove @user`, `/list`, `/status` — **included in Phase 2** | ✅ Done  |
| **WebSocket streaming**       | Replace polling with real-time event stream if Polymarket adds WS support   | Medium   |
| **Multiple Telegram targets** | Send to different chats per user or per market category                     | Medium   |
| **Web dashboard**             | Simple Flask/FastAPI page showing monitored users and recent alerts         | Low      |
| **Activity feed monitoring**  | Also monitor `/activity` endpoint for trade-level granularity               | Medium   |
| **P&L tracking**              | Track each user's running P&L and include in daily summaries                | Low      |
| **Discord integration**       | Add Discord webhook notifier as alternative/addition to Telegram            | Low      |
| **Copy trading**              | Automatically mirror positions via CLOB API (requires auth + funds)         | Low      |

---

## Dependencies (requirements.txt)

```
httpx>=0.27.0          # Async HTTP client
python-dotenv>=1.0.0   # .env file loading
pydantic>=2.0.0        # Data validation (optional, not actively used yet)
# Dev / test
pytest
pytest-asyncio
```

---

## Key Decisions

| Decision             | Choice                            | Rationale                                                          |
| -------------------- | --------------------------------- | ------------------------------------------------------------------ |
| Language             | Python 3.11+                      | Official Polymarket SDK exists in Python, rich ecosystem for bots  |
| HTTP client          | `httpx`                           | Async-native, modern, supports retries cleanly                     |
| Persistence          | JSON file (MVP) → SQLite (later)  | Zero dependencies for MVP, easy to upgrade                         |
| Polling vs WebSocket | Polling                           | Polymarket Data API is REST-only; no public WS for positions       |
| Notification         | Telegram Bot API (raw HTTP)       | Lightweight, no heavy dependency needed                            |
| Scheduling           | `asyncio` event loop              | Simple, built-in, no extra dependency for MVP                      |
| First-run behavior   | Suppress all notifications        | Avoids spam when bot starts with users who have existing positions |
| Profile management   | `config.json` + Telegram commands | File for initial bulk setup; commands for convenient runtime edits |

---

## Getting Started

### Run the bot

```powershell
# First time setup
Invoke-Build Install

# Copy and fill in credentials
cp .env.example .env

# Start the bot (Ctrl-C to stop)
Invoke-Build        # default task = Run

# Or directly
venv\bin\python.exe -m src.main
```

### Run tests

```powershell
Invoke-Build Test
```

### Add another user to monitor

Edit `config.json` and add an entry to `monitored_users`:

```json
{
  "username": "SomeTrader",
  "profile_url": "https://polymarket.com/profile/@SomeTrader",
  "wallet_address": "0x..." // leave blank to auto-resolve
}
```

The bot hot-reloads `config.json` every poll cycle — no restart needed.
