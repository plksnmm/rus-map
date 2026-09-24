from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from rus_map.api.dependencies import get_geocoding_service
from rus_map.config import get_settings
from rus_map.main import create_app
from rus_map.schemas.geocoding import GeocodingResult
from rus_map.services.geocoding import GeocodingRateLimited, GeocodingService


def geocoding_settings():
    return get_settings().model_copy(
        update={
            "geocoding_min_interval_seconds": 1.0,
            "geocoding_cache_ttl_hours": 24,
            "geocoding_cache_size": 10,
        }
    )


@pytest.mark.asyncio
async def test_geocoding_normalizes_parses_and_caches_query() -> None:
    fetcher = AsyncMock(
        return_value=[
            {
                "display_name": "Перовская улица, 66, Москва, Россия",
                "lat": "55.7433",
                "lon": "37.803",
                "boundingbox": ["55.742", "55.744", "37.802", "37.804"],
            },
            {"display_name": "Broken result", "lat": "not-a-number", "lon": "0"},
        ]
    )
    service = GeocodingService(geocoding_settings(), fetcher)

    first = await service.search("  Москва,   Перовская улица, 66 ")
    second = await service.search("москва, перовская улица, 66")

    fetcher.assert_awaited_once_with("Москва, Перовская улица, 66")
    assert first == second
    assert first == [
        GeocodingResult(
            display_name="Перовская улица, 66, Москва, Россия",
            latitude=55.7433,
            longitude=37.803,
            bounding_box=(55.742, 55.744, 37.802, 37.804),
        )
    ]


@pytest.mark.asyncio
async def test_geocoding_limits_distinct_provider_requests() -> None:
    fetcher = AsyncMock(return_value=[])
    service = GeocodingService(geocoding_settings(), fetcher)

    await service.search("Москва, Кремль")
    with pytest.raises(GeocodingRateLimited):
        await service.search("Москва, Перовская улица")


def test_geocoding_endpoint_returns_safe_results() -> None:
    service = AsyncMock(spec=GeocodingService)
    service.search.return_value = [
        GeocodingResult(
            display_name="Перовская улица, 66, Москва, Россия",
            latitude=55.7433,
            longitude=37.803,
            bounding_box=(55.742, 55.744, 37.802, 37.804),
        )
    ]
    application = create_app()
    application.dependency_overrides[get_geocoding_service] = lambda: service

    with TestClient(application) as client:
        response = client.get(
            "/api/v1/geocoding/search",
            params={"q": "Москва, Перовская улица, 66"},
        )

    assert response.status_code == 200
    assert response.json()["items"][0]["display_name"].startswith("Перовская")
    assert response.json()["attribution"] == "© OpenStreetMap contributors"
    assert response.headers["cache-control"] == "private, max-age=3600"
    service.search.assert_awaited_once_with("Москва, Перовская улица, 66")


def test_geocoding_endpoint_rejects_blank_query() -> None:
    service = AsyncMock(spec=GeocodingService)
    application = create_app()
    application.dependency_overrides[get_geocoding_service] = lambda: service

    with TestClient(application) as client:
        response = client.get("/api/v1/geocoding/search", params={"q": "   "})

    assert response.status_code == 422
    service.search.assert_not_awaited()
