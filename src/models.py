"""
Data models used across the Polymarket Position Monitor.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal


@dataclass
class MonitoredUser:
    username: str            # e.g. "Pedro-Messi"
    profile_url: str         # e.g. "https://polymarket.com/profile/@Pedro-Messi"
    wallet_address: str = "" # resolved at runtime, e.g. "0x..."


@dataclass
class Position:
    market_slug: str         # e.g. "will-oscar-piastri-be-the-2026-f1-drivers-champion"
    market_question: str     # e.g. "Will Oscar Piastri be the 2026 F1 Drivers' Champion?"
    token_id: str            # CLOB token ID (used as unique key per outcome)
    side: str                # "Yes" or "No"
    size: float              # Number of shares held
    avg_price: float         # Average entry price (0.0 – 1.0)
    current_price: float     # Current market price (0.0 – 1.0)
    value: float             # Current value in USD
    event_slug: str = ""     # e.g. "2026-f1-drivers-champion"
    condition_id: str = ""   # on-chain condition ID


EventType = Literal["new_position", "position_increased", "position_closed"]


@dataclass
class ChangeEvent:
    event_type: EventType
    user: MonitoredUser
    position: Position
    previous_size: float | None = None  # For position_increased events
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
