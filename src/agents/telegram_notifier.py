"""
Telegram Notifier Agent — sends formatted Telegram messages for each ChangeEvent.
"""
from __future__ import annotations

import logging

from src.models import ChangeEvent
from src.utils.http_client import post_json

log = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"


def _format_price(price: float) -> str:
    """Format a 0–1 price as a cent string, e.g. 0.07 → '7¢'."""
    cents = round(price * 100)
    return f"{cents}¢"


def _format_shares(size: float) -> str:
    return f"{size:,.1f}"


def _market_url(event_slug: str, market_slug: str) -> str:
    if event_slug and market_slug:
        return f"https://polymarket.com/event/{event_slug}/{market_slug}"
    if market_slug:
        return f"https://polymarket.com/event/{market_slug}"
    return "https://polymarket.com"


def _side_emoji(side: str) -> str:
    return "✅" if side.lower() == "yes" else "❌"


def format_new_position(event: ChangeEvent) -> str:
    p = event.position
    u = event.user
    url = _market_url(p.event_slug, p.market_slug)
    return (
        "🟢 *New Position Detected*\n\n"
        f"👤 {u.username}\n"
        f"📊 {p.market_question}\n\n"
        f"Side: {_side_emoji(p.side)} {p.side} @ {_format_price(p.avg_price)}\n"
        f"Shares: {_format_shares(p.size)}\n"
        f"Value: ${p.value:,.2f}\n\n"
        f"🔗 {url}"
    )


def format_position_increased(event: ChangeEvent) -> str:
    p = event.position
    u = event.user
    url = _market_url(p.event_slug, p.market_slug)
    prev = event.previous_size or 0.0
    delta = p.size - prev
    return (
        "📈 *Position Increased*\n\n"
        f"👤 {u.username}\n"
        f"📊 {p.market_question}\n\n"
        f"Side: {_side_emoji(p.side)} {p.side} @ {_format_price(p.avg_price)}\n"
        f"Shares: {_format_shares(prev)} → {_format_shares(p.size)} (+{_format_shares(delta)})\n"
        f"Value: ${p.value:,.2f}\n\n"
        f"🔗 {url}"
    )


def format_position_closed(event: ChangeEvent) -> str:
    p = event.position
    u = event.user
    url = _market_url(p.event_slug, p.market_slug)
    return (
        "🔴 *Position Closed*\n\n"
        f"👤 {u.username}\n"
        f"📊 {p.market_question}\n\n"
        f"Side: {_side_emoji(p.side)} {p.side}\n"
        f"Shares: {_format_shares(p.size)}\n\n"
        f"🔗 {url}"
    )


_FORMATTERS = {
    "new_position": format_new_position,
    "position_increased": format_position_increased,
    "position_closed": format_position_closed,
}


async def send_event(event: ChangeEvent, bot_token: str, chat_id: str) -> bool:
    """
    Send a Telegram message for *event*.

    Returns True on success, False if the send failed (error is logged but not raised
    so that other notifications are not blocked).
    """
    formatter = _FORMATTERS.get(event.event_type)
    if not formatter:
        log.warning("No formatter for event type '%s'", event.event_type)
        return False

    text = formatter(event)
    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"

    try:
        result = await post_json(url, {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        })
        ok = result.get("ok", False)
        if not ok:
            log.error("Telegram rejected message: %s", result)
        else:
            log.info("Telegram message sent for event '%s' (user: %s)", event.event_type, event.user.username)
        return bool(ok)
    except Exception as exc:
        log.error("Failed to send Telegram message: %s", exc)
        return False


async def send_startup_message(
    bot_token: str,
    chat_id: str,
    monitored_users: list,
    polling_interval: int,
) -> None:
    """Send a startup notification listing all monitored profiles."""
    lines = ["\U0001f7e2 *Polymarket Monitor is online*\n"]
    lines.append(f"Polling every *{polling_interval}s* for {len(monitored_users)} user(s):\n")
    for u in monitored_users:
        address = getattr(u, "wallet_address", "") or "(resolving...)"
        profile_url = getattr(u, "profile_url", "")
        lines.append(f"\U0001f464 [{u.username}]({profile_url})")
        lines.append(f"   `{address}`")
    text = "\n".join(lines)
    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"
    try:
        result = await post_json(url, {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        })
        if result.get("ok"):
            log.info("Startup message sent to Telegram.")
        else:
            log.warning("Telegram rejected startup message: %s", result)
    except Exception as exc:
        log.error("Failed to send startup message: %s", exc)


async def send_shutdown_message(bot_token: str, chat_id: str) -> None:
    """Send an offline notification when the bot is shutting down."""
    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"
    try:
        await post_json(url, {
            "chat_id": chat_id,
            "text": "\U0001f534 *Polymarket Monitor is offline*",
            "parse_mode": "Markdown",
        })
        log.info("Shutdown message sent to Telegram.")
    except Exception as exc:
        log.error("Failed to send shutdown message: %s", exc)


async def send_events(
    events: list[ChangeEvent],
    bot_token: str,
    chat_id: str,
    *,
    on_new_position: bool = True,
    on_position_increase: bool = True,
    on_position_closed: bool = False,
) -> int:
    """
    Send Telegram messages for all *events* that match the enabled notification types.

    Returns the count of successfully sent messages.
    """
    type_enabled = {
        "new_position": on_new_position,
        "position_increased": on_position_increase,
        "position_closed": on_position_closed,
    }

    sent = 0
    for event in events:
        if type_enabled.get(event.event_type, False):
            success = await send_event(event, bot_token, chat_id)
            if success:
                sent += 1

    return sent
