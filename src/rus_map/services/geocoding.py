import asyncio
import json
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import monotonic
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from rus_map.config import Settings
from rus_map.schemas.geocoding import GeocodingResult

MAX_PROVIDER_RESPONSE_BYTES = 1_000_000


class GeocodingUnavailable(RuntimeError):
    """Raised when the configured provider cannot return a usable response."""


class GeocodingRateLimited(RuntimeError):
    """Raised before an outbound request would violate the provider limit."""


type GeocodingFetcher = Callable[[str], Awaitable[object]]


@dataclass(frozen=True, slots=True)
class CachedSearch:
    expires_at: float
    results: tuple[GeocodingResult, ...]


class GeocodingService:
    """Search Nominatim through a small cache and a process-wide rate limit."""

    def __init__(
        self,
        settings: Settings,
        fetcher: GeocodingFetcher | None = None,
    ) -> None:
        self._settings = settings
        self._fetcher = fetcher or self._fetch_provider
        self._cache: OrderedDict[str, CachedSearch] = OrderedDict()
        self._provider_lock = asyncio.Lock()
        self._last_provider_request = float("-inf")

    async def search(self, query: str) -> list[GeocodingResult]:
        """Return cached or freshly normalized address matches."""
        cleaned = " ".join(query.split())
        cache_key = cleaned.casefold()
        cached = self._cached(cache_key)
        if cached is not None:
            return list(cached)

        async with self._provider_lock:
            cached = self._cached(cache_key)
            if cached is not None:
                return list(cached)

            now = monotonic()
            if (
                now - self._last_provider_request
                < self._settings.geocoding_min_interval_seconds
            ):
                raise GeocodingRateLimited("geocoding provider rate limit")
            self._last_provider_request = now

            payload = await self._fetcher(cleaned)

        results = self._parse_results(payload)
        self._store(cache_key, results)
        return list(results)

    def _cached(self, cache_key: str) -> tuple[GeocodingResult, ...] | None:
        cached = self._cache.get(cache_key)
        if cached is None:
            return None
        if cached.expires_at <= monotonic():
            del self._cache[cache_key]
            return None
        self._cache.move_to_end(cache_key)
        return cached.results

    def _store(
        self,
        cache_key: str,
        results: tuple[GeocodingResult, ...],
    ) -> None:
        ttl_seconds = self._settings.geocoding_cache_ttl_hours * 60 * 60
        self._cache[cache_key] = CachedSearch(
            expires_at=monotonic() + ttl_seconds,
            results=results,
        )
        self._cache.move_to_end(cache_key)
        while len(self._cache) > self._settings.geocoding_cache_size:
            self._cache.popitem(last=False)

    async def _fetch_provider(self, query: str) -> object:
        parameters = urlencode(
            {
                "q": query,
                "format": "jsonv2",
                "limit": 5,
                "countrycodes": "ru",
                "accept-language": "ru",
            }
        )
        separator = "&" if "?" in self._settings.geocoding_search_url else "?"
        url = f"{self._settings.geocoding_search_url}{separator}{parameters}"

        def fetch() -> object:
            request = Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": self._settings.geocoding_user_agent,
                },
            )
            try:
                with urlopen(
                    request,
                    timeout=self._settings.geocoding_timeout_seconds,
                ) as response:
                    body = response.read(MAX_PROVIDER_RESPONSE_BYTES + 1)
            except (HTTPError, URLError, TimeoutError, OSError) as error:
                raise GeocodingUnavailable("geocoding provider unavailable") from error

            if len(body) > MAX_PROVIDER_RESPONSE_BYTES:
                raise GeocodingUnavailable("geocoding response is too large")
            try:
                return json.loads(body)
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise GeocodingUnavailable("invalid geocoding response") from error

        return await asyncio.to_thread(fetch)

    @staticmethod
    def _parse_results(payload: object) -> tuple[GeocodingResult, ...]:
        if not isinstance(payload, list):
            raise GeocodingUnavailable("invalid geocoding response")

        parsed: list[GeocodingResult] = []
        for item in payload[:5]:
            if not isinstance(item, dict):
                continue
            try:
                display_name = str(item["display_name"]).strip()
                latitude = float(item["lat"])
                longitude = float(item["lon"])
            except (KeyError, TypeError, ValueError):
                continue
            if (
                not display_name
                or len(display_name) > 500
                or not (-90 <= latitude <= 90)
                or not (-180 <= longitude <= 180)
            ):
                continue

            bounding_box = GeocodingService._parse_bounding_box(item.get("boundingbox"))
            parsed.append(
                GeocodingResult(
                    display_name=display_name,
                    latitude=latitude,
                    longitude=longitude,
                    bounding_box=bounding_box,
                )
            )
        return tuple(parsed)

    @staticmethod
    def _parse_bounding_box(value: Any) -> tuple[float, float, float, float] | None:
        if not isinstance(value, list) or len(value) != 4:
            return None
        try:
            south, north, west, east = (float(part) for part in value)
        except (TypeError, ValueError):
            return None
        if not (-90 <= south <= north <= 90 and -180 <= west <= east <= 180):
            return None
        return south, north, west, east
