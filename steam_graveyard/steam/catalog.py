"""Supported Steam Store catalog client."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from email.utils import parsedate_to_datetime
from time import time

import httpx

from steam_graveyard.errors import CatalogError, ConfigurationError
from steam_graveyard.models import CatalogEntry

CATALOG_ENDPOINT = "https://partner.steam-api.com/IStoreService/GetAppList/v1/"


class SteamCatalogClient:
    """Fetch complete, paginated game catalogs from IStoreService."""

    def __init__(
        self,
        api_key: str | None,
        *,
        timeout: float = 20.0,
        max_results: int = 50_000,
        max_retries: int = 3,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.max_results = max_results
        self.max_retries = max_retries
        self._client_factory = client_factory or (
            lambda: httpx.AsyncClient(timeout=self.timeout, follow_redirects=True)
        )

    async def fetch_all_games(self) -> list[CatalogEntry]:
        if not self.api_key:
            raise ConfigurationError(
                "STEAM_API_KEY is required for catalog updates. Local browsing remains available."
            )
        entries: dict[int, CatalogEntry] = {}
        last_appid = 0
        async with self._client_factory() as client:
            while True:
                body = {
                    "include_games": True,
                    "include_dlc": False,
                    "include_software": False,
                    "include_videos": False,
                    "include_hardware": False,
                    "last_appid": last_appid,
                    "max_results": self.max_results,
                }
                response = await self._request_with_retry(
                    client,
                    params={"key": self.api_key, "input_json": json.dumps(body)},
                )
                payload = response.json().get("response", {})
                raw_apps = payload.get("apps", [])
                if not isinstance(raw_apps, list):
                    raise CatalogError("Steam catalog response did not contain an apps list.")
                page: list[CatalogEntry] = []
                for raw in raw_apps:
                    try:
                        entry = CatalogEntry.model_validate(raw)
                    except (TypeError, ValueError) as exc:
                        raise CatalogError(
                            f"Steam returned an invalid catalog entry: {exc}"
                        ) from exc
                    if entry.appid in entries:
                        raise CatalogError(f"Steam returned duplicate AppID {entry.appid}.")
                    entries[entry.appid] = entry
                    page.append(entry)
                have_more = bool(payload.get("have_more_results", False))
                if not page:
                    if have_more:
                        raise CatalogError(
                            "Steam reported more results but returned an empty page."
                        )
                    break
                next_appid = int(payload.get("last_appid", page[-1].appid))
                if next_appid <= last_appid:
                    raise CatalogError("Steam catalog pagination cursor did not advance.")
                last_appid = next_appid
                if not have_more and len(page) < self.max_results:
                    break
                if not have_more and "have_more_results" in payload:
                    break
        return sorted(entries.values(), key=lambda item: item.appid)

    async def _request_with_retry(
        self,
        client: httpx.AsyncClient,
        *,
        params: dict[str, str],
    ) -> httpx.Response:
        for attempt in range(self.max_retries + 1):
            try:
                response = await client.get(CATALOG_ENDPOINT, params=params)
            except httpx.RequestError as exc:
                if attempt >= self.max_retries:
                    raise CatalogError(
                        f"Steam catalog request failed ({type(exc).__name__}); "
                        "the API key was not included in this error."
                    ) from exc
                await asyncio.sleep(2**attempt)
                continue
            if response.status_code < 400:
                try:
                    response.json()
                except ValueError as exc:
                    raise CatalogError("Steam returned a non-JSON catalog response.") from exc
                return response
            if response.status_code not in {429, 500, 502, 503, 504} or attempt >= self.max_retries:
                raise CatalogError(
                    f"Steam catalog request failed with HTTP {response.status_code}."
                )
            await asyncio.sleep(self._retry_delay(response, attempt))
        raise CatalogError("Steam catalog retry loop ended unexpectedly.")

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        value = response.headers.get("Retry-After")
        if value:
            try:
                return min(60.0, max(0.0, float(value)))
            except ValueError:
                try:
                    retry_at = parsedate_to_datetime(value).timestamp()
                    return min(60.0, max(0.0, retry_at - time()))
                except (TypeError, ValueError, OverflowError):
                    pass
        return float(2**attempt)
