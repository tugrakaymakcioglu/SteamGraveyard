"""Non-blocking Steam connectivity probe."""

from __future__ import annotations

import httpx


async def steam_is_reachable(*, timeout: float = 3.0) -> bool:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.head("https://store.steampowered.com/")
        return response.status_code < 500
    except httpx.RequestError:
        return False
