"""
Config loader — reads .env and config.json into typed config objects.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (one level above src/)
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

CONFIG_PATH = _ROOT / "config.json"


@dataclass
class NotificationSettings:
    on_new_position: bool = True
    on_position_increase: bool = True
    on_position_closed: bool = False


@dataclass
class MonitoredUserConfig:
    username: str
    profile_url: str
    wallet_address: str = ""  # optional: skip resolution if provided


@dataclass
class AppConfig:
    telegram_bot_token: str
    telegram_chat_id: str
    polling_interval_seconds: int
    monitored_users: list[MonitoredUserConfig]
    notifications: NotificationSettings
    first_run_suppress_notifications: bool
    authorized_chat_ids: list[str]


def load_config() -> AppConfig:
    """Load and validate configuration from .env and config.json."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not token:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN is not set. Copy .env.example to .env and fill in your credentials."
        )
    if not chat_id:
        raise ValueError(
            "TELEGRAM_CHAT_ID is not set. Copy .env.example to .env and fill in your credentials."
        )

    raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    users = [
        MonitoredUserConfig(
            username=u["username"],
            profile_url=u["profile_url"],
            wallet_address=u.get("wallet_address", ""),
        )
        for u in raw.get("monitored_users", [])
    ]

    notif_raw = raw.get("notifications", {})
    notifications = NotificationSettings(
        on_new_position=notif_raw.get("on_new_position", True),
        on_position_increase=notif_raw.get("on_position_increase", True),
        on_position_closed=notif_raw.get("on_position_closed", False),
    )

    return AppConfig(
        telegram_bot_token=token,
        telegram_chat_id=chat_id,
        polling_interval_seconds=int(raw.get("polling_interval_seconds", 30)),
        monitored_users=users,
        notifications=notifications,
        first_run_suppress_notifications=raw.get("first_run_suppress_notifications", True),
        authorized_chat_ids=raw.get("authorized_chat_ids", []),
    )


def reload_monitored_users() -> list[MonitoredUserConfig]:
    """Re-read only the monitored_users list from config.json (hot-reload)."""
    raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return [
        MonitoredUserConfig(
            username=u["username"],
            profile_url=u["profile_url"],
            wallet_address=u.get("wallet_address", ""),
        )
        for u in raw.get("monitored_users", [])
    ]
