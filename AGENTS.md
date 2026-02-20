# Agents — Polymarket Position Monitor Bot

This document defines the agents (components/modules) that compose the Polymarket Position Monitor system. Each agent has a single responsibility and communicates through well-defined interfaces.

---

## 1. Profile Resolver Agent

**Responsibility:** Resolve Polymarket usernames (`@Pedro-Messi`) into wallet addresses required by the Data API.

**How it works:**

- Receives a Polymarket profile URL or `@username`.
- Queries the Gamma API `GET /public-search` or scrapes the profile page to extract the user's Polygon wallet address.
- Caches the `username → address` mapping so it doesn't re-resolve on every poll cycle.

**Inputs:** `@username` or profile URL (e.g. `https://polymarket.com/profile/@Pedro-Messi`)  
**Outputs:** Polygon wallet address (`0x...`)

**API Used:** `https://gamma-api.polymarket.com/public-search`

---

## 2. Position Poller Agent

**Responsibility:** Periodically fetch the current active positions for each monitored user.

**How it works:**

- For each monitored wallet address, calls the Data API `GET /positions?user={address}`.
- Returns the full list of current active positions including market name, side (Yes/No), size, avg price, current price, and value.
- Respects rate limits (150 req/10s for `/positions`).

**Inputs:** List of wallet addresses + polling interval  
**Outputs:** Raw position data per user (array of position objects)

**API Used:** `https://data-api.polymarket.com/positions?user={address}`

---

## 3. Change Detector Agent

**Responsibility:** Compare the latest fetched positions against the previously known state and identify new/changed positions.

**How it works:**

- Maintains a local state store (JSON file or SQLite) of each user's last-known positions.
- On each poll cycle, diffs the fresh positions against the stored snapshot.
- Detects:
  - **New positions** — a market/token that didn't exist before.
  - **Position increases** — existing position with more shares than before (optional, configurable).
  - **Closed positions** — position that disappeared (optional, configurable).
- Emits change events with full context (user, market question, side, shares, price, value).

**Inputs:** Current positions (from Poller) + stored state  
**Outputs:** List of change events (`new_position`, `position_increased`, `position_closed`)

---

## 4. Telegram Notifier Agent

**Responsibility:** Send formatted Telegram messages when position changes are detected.

**How it works:**

- Receives change events from the Change Detector.
- Formats a human-readable Telegram message with:
  - User who made the trade (`@username`)
  - Market question (e.g. "Will George Russell be the 2026 F1 Drivers' Champion?")
  - Side (Yes / No) and price paid
  - Number of shares and total value
  - Direct link to the market on Polymarket
- Sends via Telegram Bot API (`POST https://api.telegram.org/bot<TOKEN>/sendMessage`).
- Supports sending to one or more chat IDs (group chats, channels, or DMs).
- Handles Telegram rate limits and retries on failure.

**Inputs:** Change events  
**Outputs:** Telegram messages sent (with delivery confirmation logging)

**API Used:** `https://api.telegram.org/bot<TOKEN>/sendMessage`

---

## 5. State Manager Agent

**Responsibility:** Persist and retrieve the known position state between poll cycles (and across restarts).

**How it works:**

- Stores per-user position snapshots keyed by wallet address.
- Supports two backends (configurable):
  - **JSON file** — simple, zero-dependency, good for single-instance deploys.
  - **SQLite** — better for larger scale or if query flexibility is needed later.
- Provides `get_state(address)` and `save_state(address, positions)` methods.
- Handles first-run gracefully (no prior state = all positions treated as "existing" to avoid a notification flood on startup).

**Inputs:** Wallet address + position data  
**Outputs:** Stored/retrieved state

---

## 6. Telegram Command Handler Agent

**Responsibility:** Accept Telegram commands to manage the monitored user list at runtime.

**How it works:**

- Listens for incoming Telegram messages (via polling or webhook) on the bot.
- Supports the following commands:
  - `/add @username` — Add a new Polymarket profile to monitor. Resolves the username immediately via Profile Resolver and confirms success.
  - `/remove @username` — Stop monitoring a profile. Cleans up cached address and stored state.
  - `/list` — Show all currently monitored profiles with their wallet addresses.
  - `/status` — Show bot uptime, last poll time, number of monitored users, and last detected change.
- Persists changes to `config.json` so they survive restarts.
- Validates usernames before adding (checks that the profile exists on Polymarket).
- Only responds to commands from authorized chat IDs (configured in `.env`).

**Inputs:** Telegram messages (commands)  
**Outputs:** Updated monitored user list + confirmation messages back to Telegram

**API Used:** `https://api.telegram.org/bot<TOKEN>/getUpdates` (or webhook)

---

## 7. Scheduler / Orchestrator Agent

**Responsibility:** Coordinate the entire pipeline on a configurable interval.

**How it works:**

- Runs the following pipeline on a loop (e.g., every 30–60 seconds):
  1. Reload monitored user list (picks up changes from **Telegram Command Handler** or `config.json` edits)
  2. For each monitored profile → **Profile Resolver** (cached) → wallet address
  3. **Position Poller** → fetch current positions
  4. **Change Detector** → diff against stored state
  5. If changes found → **Telegram Notifier** → send alerts
  6. **State Manager** → save updated snapshot
- Runs the **Telegram Command Handler** concurrently (separate async task).
- Handles errors gracefully (one user failing doesn't block others).
- Logs each cycle with timestamps for observability.
- Hot-reloads the monitored user list each cycle from the shared config.

**Inputs:** Config file (users to monitor, polling interval, Telegram settings)  
**Outputs:** Orchestrated pipeline execution

---

## Agent Communication Flow

```
                    ┌──────────────────┐
                    │  Telegram Command │  /add, /remove, /list, /status
                    │  Handler          │◄──── Telegram Chat
                    └────────┬─────────┘
                             │ writes
                             ▼
┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Config     │────▶│  Profile Resolver │────▶│  Position Poller │
│ (config.json)│     │  (@user → 0x...) │     │  (Data API)      │
└─────────────┘     └──────────────────┘     └────────┬─────────┘
                                                       │
                                                       ▼
                    ┌──────────────────┐     ┌──────────────────┐
                    │  Telegram        │◀────│  Change Detector │
                    │  Notifier        │     │  (diff engine)   │
                    └──────────────────┘     └────────┬─────────┘
                                                       │
                                                       ▼
                                              ┌──────────────────┐
                                              │  State Manager   │
                                              │  (persistence)   │
                                              └──────────────────┘
```

---

## Tech Stack

| Component        | Technology                        |
| ---------------- | --------------------------------- |
| Language         | Python 3.11+                      |
| HTTP Client      | `httpx` (async) or `requests`     |
| Telegram         | `python-telegram-bot` or raw HTTP |
| Persistence      | JSON file (default) / SQLite      |
| Scheduling       | `asyncio` loop or `APScheduler`   |
| Config           | `.env` + `config.json`            |
| Logging          | Python `logging` module           |
| Containerization | Docker (optional)                 |
