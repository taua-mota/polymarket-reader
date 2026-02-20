"""
Position Poller Agent — fetches the current active positions for a given wallet address.
"""
from __future__ import annotations

import logging

from src.models import Position
from src.utils.http_client import get_json

log = logging.getLogger(__name__)

DATA_API_BASE = "https://data-api.polymarket.com"


async def fetch_positions(wallet_address: str) -> list[Position]:
    """
    Fetch all current active positions for *wallet_address* from the Data API.

    Parameters
    ----------
    wallet_address : str
        The user's Polygon wallet address (0x...).

    Returns
    -------
    list[Position]
        Parsed position objects. Empty list if the user has no open positions.
    """
    log.debug("Fetching positions for %s …", wallet_address)

    raw: list | dict = await get_json(
        f"{DATA_API_BASE}/positions",
        params={"user": wallet_address},
    )

    # The API returns a list of position objects directly
    if isinstance(raw, dict):
        # Some endpoints wrap in {"positions": [...]} or {"data": [...]}
        raw = raw.get("positions") or raw.get("data") or []

    positions: list[Position] = []
    for item in raw:
        try:
            positions.append(_parse_position(item))
        except Exception as exc:
            log.warning("Failed to parse position entry: %s — %s", item, exc)

    log.info("Fetched %d position(s) for %s", len(positions), wallet_address)
    return positions


def _parse_position(item: dict) -> Position:
    """Convert a raw API response dict into a Position dataclass."""
    return Position(
        market_slug=item.get("slug") or item.get("marketSlug") or item.get("market_slug") or "",
        market_question=item.get("title") or item.get("marketQuestion") or item.get("question") or "",
        token_id=str(item.get("asset") or item.get("tokenId") or item.get("token_id") or ""),
        side=_parse_side(item),
        size=float(item.get("size") or item.get("shares") or 0),
        avg_price=float(item.get("avgPrice") or item.get("avg_price") or item.get("averagePrice") or 0),
        current_price=float(item.get("curPrice") or item.get("currentPrice") or item.get("current_price") or 0),
        value=float(item.get("currentValue") or item.get("value") or 0),
        event_slug=item.get("eventSlug") or item.get("event_slug") or "",
        condition_id=item.get("conditionId") or item.get("condition_id") or "",
    )


def _parse_side(item: dict) -> str:
    """Extract the Yes/No side from a position item."""
    # The outcome field holds "Yes" / "No" in most API shapes
    outcome = item.get("outcome") or item.get("side") or ""
    if outcome:
        return str(outcome).capitalize()
    # Fallback: some shapes use a boolean "isYes" flag
    is_yes = item.get("isYes")
    if is_yes is True:
        return "Yes"
    if is_yes is False:
        return "No"
    return "Unknown"
