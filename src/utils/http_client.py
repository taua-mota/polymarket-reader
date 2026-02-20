"""
Shared async HTTP client with retry and timeout logic.
"""
from __future__ import annotations

import asyncio
import logging

import httpx

log = logging.getLogger(__name__)

# Default timeouts (seconds)
_CONNECT_TIMEOUT = 10.0
_READ_TIMEOUT = 15.0

# Retry settings
_MAX_RETRIES = 3
_BACKOFF_DELAYS = [5, 15, 45]  # seconds between attempts


def _build_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(connect=_CONNECT_TIMEOUT, read=_READ_TIMEOUT, write=10.0, pool=5.0),
        follow_redirects=True,
        headers={"User-Agent": "polymarket-position-monitor/1.0"},
    )


# Module-level shared client (initialised lazily per async context)
_client: httpx.AsyncClient | None = None


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = _build_client()
    return _client


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


async def get_json(url: str, params: dict | None = None) -> dict | list:
    """
    Perform a GET request and return the parsed JSON response.
    Retries up to _MAX_RETRIES times with exponential backoff on transient errors.
    Raises httpx.HTTPStatusError for non-2xx responses after all retries are exhausted.
    """
    client = await get_client()

    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            last_exc = exc
            delay = _BACKOFF_DELAYS[min(attempt, len(_BACKOFF_DELAYS) - 1)]
            log.warning(
                "Request to %s failed (attempt %d/%d): %s — retrying in %ds",
                url, attempt + 1, _MAX_RETRIES, exc, delay,
            )
            await asyncio.sleep(delay)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                retry_after = int(exc.response.headers.get("Retry-After", "10"))
                log.warning("Rate-limited by %s — waiting %ds", url, retry_after)
                await asyncio.sleep(retry_after)
                last_exc = exc
            else:
                raise

    raise RuntimeError(f"All {_MAX_RETRIES} attempts to GET {url} failed") from last_exc


async def post_json(url: str, payload: dict) -> dict:
    """POST JSON payload and return the parsed JSON response with retry logic."""
    client = await get_client()

    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            last_exc = exc
            delay = _BACKOFF_DELAYS[min(attempt, len(_BACKOFF_DELAYS) - 1)]
            log.warning(
                "POST to %s failed (attempt %d/%d): %s — retrying in %ds",
                url, attempt + 1, _MAX_RETRIES, exc, delay,
            )
            await asyncio.sleep(delay)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                retry_after = int(exc.response.headers.get("Retry-After", "10"))
                log.warning("Rate-limited by %s — waiting %ds", url, retry_after)
                await asyncio.sleep(retry_after)
                last_exc = exc
            else:
                raise

    raise RuntimeError(f"All {_MAX_RETRIES} attempts to POST {url} failed") from last_exc
