"""
Change Detector Agent — diffs current positions against the stored snapshot
and emits ChangeEvent objects for each detected change.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.models import ChangeEvent, MonitoredUser, Position

log = logging.getLogger(__name__)


def detect_changes(
    user: MonitoredUser,
    current_positions: list[Position],
    previous_positions: list[Position],
    *,
    detect_increases: bool = True,
    detect_closures: bool = False,
) -> list[ChangeEvent]:
    """
    Compare *current_positions* to *previous_positions* and return a list of
    ChangeEvent objects describing what changed.

    Parameters
    ----------
    user : MonitoredUser
        The user whose positions are being diffed.
    current_positions : list[Position]
        Freshly fetched positions.
    previous_positions : list[Position]
        Positions from the last stored state snapshot.
    detect_increases : bool
        Whether to emit events when an existing position grows in size.
    detect_closures : bool
        Whether to emit events when a position disappears entirely.

    Returns
    -------
    list[ChangeEvent]
        Ordered list of change events (empty if nothing changed).
    """
    events: list[ChangeEvent] = []
    now = datetime.now(timezone.utc)

    # Build lookup maps keyed by token_id (unique per market outcome)
    prev_map: dict[str, Position] = {p.token_id: p for p in previous_positions if p.token_id}
    curr_map: dict[str, Position] = {p.token_id: p for p in current_positions if p.token_id}

    # Detect new positions and position increases
    for token_id, curr in curr_map.items():
        if token_id not in prev_map:
            log.info(
                "[%s] New position detected: %s %s @ %.2f¢",
                user.username, curr.market_question, curr.side, curr.avg_price * 100
            )
            events.append(
                ChangeEvent(
                    event_type="new_position",
                    user=user,
                    position=curr,
                    previous_size=None,
                    detected_at=now,
                )
            )
        elif detect_increases:
            prev = prev_map[token_id]
            # Consider a meaningful increase as at least 1 share growth
            if curr.size > prev.size + 0.5:
                log.info(
                    "[%s] Position increased: %s %s — %.2f → %.2f shares",
                    user.username, curr.market_question, curr.side, prev.size, curr.size
                )
                events.append(
                    ChangeEvent(
                        event_type="position_increased",
                        user=user,
                        position=curr,
                        previous_size=prev.size,
                        detected_at=now,
                    )
                )

    # Detect closed positions (optional)
    if detect_closures:
        for token_id, prev in prev_map.items():
            if token_id not in curr_map:
                log.info(
                    "[%s] Position closed: %s %s",
                    user.username, prev.market_question, prev.side
                )
                events.append(
                    ChangeEvent(
                        event_type="position_closed",
                        user=user,
                        position=prev,
                        previous_size=prev.size,
                        detected_at=now,
                    )
                )

    return events
