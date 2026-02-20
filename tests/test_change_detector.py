"""
Tests for the Change Detector agent.

Run with:  pytest tests/test_change_detector.py
"""
from __future__ import annotations

from src.agents.change_detector import detect_changes
from src.models import MonitoredUser, Position


def _make_user() -> MonitoredUser:
    return MonitoredUser(
        username="test-user",
        profile_url="https://polymarket.com/profile/@test-user",
        wallet_address="0x1234",
    )


def _make_position(token_id: str, size: float = 100.0, side: str = "Yes") -> Position:
    return Position(
        market_slug="test-market",
        market_question="Test market question?",
        token_id=token_id,
        side=side,
        size=size,
        avg_price=0.5,
        current_price=0.5,
        value=size * 0.5,
        event_slug="test-event",
    )


class TestDetectChanges:
    def test_no_changes(self):
        user = _make_user()
        positions = [_make_position("tok1", 100.0)]
        events = detect_changes(user, positions, positions)
        assert events == []

    def test_new_position_detected(self):
        user = _make_user()
        previous = []
        current = [_make_position("tok1", 100.0)]
        events = detect_changes(user, current, previous)
        assert len(events) == 1
        assert events[0].event_type == "new_position"
        assert events[0].position.token_id == "tok1"
        assert events[0].previous_size is None

    def test_position_increase_detected(self):
        user = _make_user()
        previous = [_make_position("tok1", 100.0)]
        current = [_make_position("tok1", 200.0)]
        events = detect_changes(user, current, previous, detect_increases=True)
        assert len(events) == 1
        assert events[0].event_type == "position_increased"
        assert events[0].previous_size == 100.0
        assert events[0].position.size == 200.0

    def test_small_increase_ignored(self):
        user = _make_user()
        previous = [_make_position("tok1", 100.0)]
        current = [_make_position("tok1", 100.3)]  # less than 0.5 threshold
        events = detect_changes(user, current, previous, detect_increases=True)
        assert events == []

    def test_position_increase_disabled(self):
        user = _make_user()
        previous = [_make_position("tok1", 100.0)]
        current = [_make_position("tok1", 200.0)]
        events = detect_changes(user, current, previous, detect_increases=False)
        assert events == []

    def test_position_closed_detected(self):
        user = _make_user()
        previous = [_make_position("tok1", 100.0)]
        current = []
        events = detect_changes(user, current, previous, detect_closures=True)
        assert len(events) == 1
        assert events[0].event_type == "position_closed"

    def test_position_closed_disabled(self):
        user = _make_user()
        previous = [_make_position("tok1", 100.0)]
        current = []
        events = detect_changes(user, current, previous, detect_closures=False)
        assert events == []

    def test_multiple_new_positions(self):
        user = _make_user()
        previous = [_make_position("tok1")]
        current = [_make_position("tok1"), _make_position("tok2"), _make_position("tok3")]
        events = detect_changes(user, current, previous)
        new_events = [e for e in events if e.event_type == "new_position"]
        assert len(new_events) == 2

    def test_user_and_position_attached_to_event(self):
        user = _make_user()
        events = detect_changes(user, [_make_position("tok1")], [])
        assert events[0].user.username == "test-user"
        assert events[0].position.token_id == "tok1"
