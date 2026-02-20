"""
Tests for the Profile Resolver agent.

Run with:  pytest tests/test_profile_resolver.py
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from src.agents.profile_resolver import _extract_address, clear_cache, resolve_username


# ---------------------------------------------------------------------------
# Unit tests for _extract_address (no I/O)
# ---------------------------------------------------------------------------

class TestExtractAddress:
    def test_users_key(self):
        data = {
            "users": [
                {"username": "pedro-messi", "walletAddress": "0xABC"}
            ]
        }
        assert _extract_address(data, "pedro-messi") == "0xABC"

    def test_case_insensitive_match(self):
        data = {
            "users": [
                {"username": "Pedro-Messi", "walletAddress": "0xDEF"}
            ]
        }
        assert _extract_address(data, "pedro-messi") == "0xDEF"

    def test_single_result_fallback(self):
        data = [{"username": "someone", "walletAddress": "0x123"}]
        assert _extract_address(data, "no-match") == "0x123"

    def test_no_match_no_address(self):
        data = {"users": []}
        assert _extract_address(data, "ghost") is None

    def test_address_alternative_fields(self):
        data = {"users": [{"username": "alice", "proxyWallet": "0xPROXY"}]}
        assert _extract_address(data, "alice") == "0xPROXY"


# ---------------------------------------------------------------------------
# Integration-style tests with mocked HTTP
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_username_success():
    clear_cache()
    mock_response = {
        "users": [{"username": "pedro-messi", "walletAddress": "0xCAFE"}]
    }
    with patch("src.agents.profile_resolver.get_json", new=AsyncMock(return_value=mock_response)):
        address = await resolve_username("Pedro-Messi")
    assert address == "0xCAFE"


@pytest.mark.asyncio
async def test_resolve_username_uses_cache():
    clear_cache()
    mock_response = {
        "users": [{"username": "pedro-messi", "walletAddress": "0xCAFE"}]
    }
    with patch("src.agents.profile_resolver.get_json", new=AsyncMock(return_value=mock_response)) as mock_get:
        await resolve_username("Pedro-Messi")
        await resolve_username("pedro-messi")  # second call — should use cache
    assert mock_get.call_count == 1


@pytest.mark.asyncio
async def test_resolve_username_not_found_raises():
    clear_cache()
    with patch("src.agents.profile_resolver.get_json", new=AsyncMock(return_value={"users": []})):
        with pytest.raises(ValueError, match="Could not resolve"):
            await resolve_username("ghost-user")
