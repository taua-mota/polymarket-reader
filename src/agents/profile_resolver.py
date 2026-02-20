"""
Profile Resolver Agent — resolves @username → Polygon wallet address.

Uses the Gamma API public-search endpoint and caches results in memory
so the resolution only happens once per username per process lifetime.
"""
from __future__ import annotations

import logging

from src.utils.http_client import get_json

log = logging.getLogger(__name__)

GAMMA_API_BASE = "https://gamma-api.polymarket.com"

# In-memory cache: username (lowercase, no @) → wallet address
_cache: dict[str, str] = {}


async def resolve_username(username: str) -> str:
    """
    Resolve a Polymarket @username to a Polygon wallet address.

    Parameters
    ----------
    username : str
        Username with or without leading '@', e.g. 'Pedro-Messi' or '@Pedro-Messi'.

    Returns
    -------
    str
        The wallet address, e.g. '0x1234...'.

    Raises
    ------
    ValueError
        If the username cannot be found on Polymarket.
    """
    clean = username.lstrip("@").strip()
    cache_key = clean.lower()

    if cache_key in _cache:
        log.debug("Cache hit for username '%s' → %s", clean, _cache[cache_key])
        return _cache[cache_key]

    log.info("Resolving username '%s' via Gamma API …", clean)

    data = await get_json(
        f"{GAMMA_API_BASE}/public-search",
        params={"query": clean},
    )

    address = _extract_address(data, clean)
    if not address:
        raise ValueError(
            f"Could not resolve Polymarket username '{clean}'. "
            "Check that the profile exists and that the username is spelled correctly."
        )

    log.info("Resolved '%s' → %s", clean, address)
    _cache[cache_key] = address
    return address


def _extract_address(data: dict | list, username: str) -> str | None:
    """
    Parse the Gamma API /public-search response and extract the wallet address.

    The response structure can vary; we handle the known shapes:
      - {"users": [...]} with each user having a "walletAddress" field
      - A direct list of profile objects
    """
    candidates: list[dict] = []

    if isinstance(data, dict):
        # Common shapes: {"users": [...], "markets": [...]}
        candidates = data.get("users", []) or data.get("results", [])
    elif isinstance(data, list):
        candidates = data

    lower_name = username.lower()

    for profile in candidates:
        if not isinstance(profile, dict):
            continue
        # Match by username field (case-insensitive)
        profile_username = (
            profile.get("username") or profile.get("name") or profile.get("pseudonym") or ""
        ).lower()
        if profile_username == lower_name or lower_name in profile_username:
            # Try common field names for the wallet address
            address = (
                profile.get("walletAddress")
                or profile.get("address")
                or profile.get("proxyWallet")
                or profile.get("wallet")
                or ""
            )
            if address and address.startswith("0x"):
                return address

    # Fallback: return the first profile's address if there's an exact single result
    if len(candidates) == 1 and isinstance(candidates[0], dict):
        profile = candidates[0]
        address = (
            profile.get("walletAddress")
            or profile.get("address")
            or profile.get("proxyWallet")
            or profile.get("wallet")
            or ""
        )
        if address and address.startswith("0x"):
            return address

    return None


def clear_cache() -> None:
    """Clear the in-memory username → address cache (useful for testing)."""
    _cache.clear()
