"""
Tests for the Telegram Notifier agent.

Run with:  pytest tests/test_telegram_notifier.py
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from src.agents.telegram_notifier import (
    format_new_position,
    format_position_closed,
    format_position_increased,
    send_events,
)
from src.models import ChangeEvent, MonitoredUser, Position


def _make_user() -> MonitoredUser:
    return MonitoredUser(
        username="Pedro-Messi",
        profile_url="https://polymarket.com/profile/@Pedro-Messi",
        wallet_address="0xABCD",
    )


def _make_position() -> Position:
    return Position(
        market_slug="will-oscar-piastri-be-the-2026-f1-drivers-champion",
        market_question="Will Oscar Piastri be the 2026 F1 Drivers' Champion?",
        token_id="999",
        side="Yes",
        size=8583.2,
        avg_price=0.07,
        current_price=0.06,
        value=514.99,
        event_slug="2026-f1-drivers-champion",
    )


class TestFormatters:
    def test_format_new_position_contains_username(self):
        event = ChangeEvent(event_type="new_position", user=_make_user(), position=_make_position())
        msg = format_new_position(event)
        assert "Pedro-Messi" in msg
        assert "✅" in msg  # Yes side
        assert "8,583.2" in msg
        assert "$514.99" in msg
        assert "polymarket.com" in msg

    def test_format_new_position_no_side(self):
        pos = _make_position()
        pos.side = "No"
        event = ChangeEvent(event_type="new_position", user=_make_user(), position=pos)
        msg = format_new_position(event)
        assert "❌" in msg

    def test_format_position_increased(self):
        event = ChangeEvent(
            event_type="position_increased",
            user=_make_user(),
            position=_make_position(),
            previous_size=4000.0,
        )
        msg = format_position_increased(event)
        assert "4,000.0" in msg
        assert "8,583.2" in msg
        assert "+4,583.2" in msg

    def test_format_position_closed(self):
        event = ChangeEvent(event_type="position_closed", user=_make_user(), position=_make_position())
        msg = format_position_closed(event)
        assert "🔴" in msg
        assert "Pedro-Messi" in msg


class TestSendEvents:
    @pytest.mark.asyncio
    async def test_sends_new_position_when_enabled(self):
        event = ChangeEvent(event_type="new_position", user=_make_user(), position=_make_position())
        mock_result = {"ok": True, "result": {}}
        with patch("src.agents.telegram_notifier.post_json", new=AsyncMock(return_value=mock_result)):
            sent = await send_events([event], "TOKEN", "CHAT", on_new_position=True)
        assert sent == 1

    @pytest.mark.asyncio
    async def test_skips_new_position_when_disabled(self):
        event = ChangeEvent(event_type="new_position", user=_make_user(), position=_make_position())
        with patch("src.agents.telegram_notifier.post_json", new=AsyncMock()) as mock_post:
            sent = await send_events([event], "TOKEN", "CHAT", on_new_position=False)
        assert sent == 0
        mock_post.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_zero_on_telegram_failure(self):
        event = ChangeEvent(event_type="new_position", user=_make_user(), position=_make_position())
        with patch("src.agents.telegram_notifier.post_json", new=AsyncMock(side_effect=Exception("Network error"))):
            sent = await send_events([event], "TOKEN", "CHAT", on_new_position=True)
        assert sent == 0
