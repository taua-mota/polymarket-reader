"""
State Manager Agent — persists and retrieves per-user position snapshots.

Backend: JSON file at data/state.json (zero external dependencies for MVP).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from src.models import Position

log = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent.parent
_STATE_PATH = _ROOT / "data" / "state.json"


def _load_raw() -> dict[str, list[dict]]:
    """Load the raw state file. Returns an empty dict if the file doesn't exist or is corrupt."""
    if not _STATE_PATH.exists():
        return {}
    try:
        return json.loads(_STATE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("State file is corrupt or unreadable (%s) — starting with empty state.", exc)
        return {}


def _save_raw(state: dict[str, list[dict]]) -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _position_to_dict(p: Position) -> dict:
    return {
        "market_slug": p.market_slug,
        "market_question": p.market_question,
        "token_id": p.token_id,
        "side": p.side,
        "size": p.size,
        "avg_price": p.avg_price,
        "current_price": p.current_price,
        "value": p.value,
        "event_slug": p.event_slug,
        "condition_id": p.condition_id,
    }


def _dict_to_position(d: dict) -> Position:
    return Position(
        market_slug=d.get("market_slug", ""),
        market_question=d.get("market_question", ""),
        token_id=d.get("token_id", ""),
        side=d.get("side", "Unknown"),
        size=float(d.get("size", 0)),
        avg_price=float(d.get("avg_price", 0)),
        current_price=float(d.get("current_price", 0)),
        value=float(d.get("value", 0)),
        event_slug=d.get("event_slug", ""),
        condition_id=d.get("condition_id", ""),
    )


def get_state(wallet_address: str) -> list[Position] | None:
    """
    Retrieve the last-known positions for *wallet_address*.

    Returns None if this is the first time we've seen this address (first run).
    Returns an empty list if the user had no positions at last save.
    """
    raw = _load_raw()
    if wallet_address not in raw:
        return None  # Signals "first run" for this address
    return [_dict_to_position(d) for d in raw[wallet_address]]


def save_state(wallet_address: str, positions: list[Position]) -> None:
    """Persist *positions* as the current snapshot for *wallet_address*."""
    raw = _load_raw()
    raw[wallet_address] = [_position_to_dict(p) for p in positions]
    _save_raw(raw)
    log.debug("Saved %d position(s) for %s", len(positions), wallet_address)


def is_first_run(wallet_address: str) -> bool:
    """Return True if we have no stored state for this wallet address yet."""
    raw = _load_raw()
    return wallet_address not in raw
