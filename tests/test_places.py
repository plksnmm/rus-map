from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from rus_map.api.dependencies import get_place_repository
from rus_map.main import app
from rus_map.repositories.place import (
    NewPlace,
    PlaceDetailRecord,
    PlacePage,
    PlaceRecord,
    PlaceRepository,
)

client = TestClient(app)


def test_list_places_returns_empty_collection() -> None:
    repository = AsyncMock(spec=PlaceRepository)
    repository.list.return_value = PlacePage(items=[], total=0)
    app.dependency_overrides[get_place_repository] = lambda: repository

    try:
        response = client.get("/api/v1/places")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
    }


def test_list_places_returns_repository_data() -> None:
    place_id = uuid4()
    repository = AsyncMock(spec=PlaceRepository)
    repository.list.return_value = PlacePage(
        items=[
            PlaceRecord(
                id=place_id,
                title="Завод Красный богатырь",
                latitude=55.8031,
                longitude=37.6917,
            ),
        ],
        total=1,
    )
    app.dependency_overrides[get_place_repository] = lambda: repository

    try:
        response = client.get("/api/v1/places")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": str(place_id),
                "title": "Завод Красный богатырь",
                "latitude": 55.8031,
                "longitude": 37.6917,
            },
        ],
        "total": 1,
    }


def test_get_place_returns_repository_data() -> None:
    place_id = uuid4()
    timestamp = datetime(2026, 9, 3, 20, 22, tzinfo=UTC)
    repository = AsyncMock(spec=PlaceRepository)
    repository.get_by_id.return_value = PlaceDetailRecord(
        id=place_id,
        title="Сысертский электротехнический завод",
        description="Советское предприятие в исторических корпусах.",
        latitude=56.494711,
        longitude=60.809612,
        created_at=timestamp,
        updated_at=timestamp,
    )
    app.dependency_overrides[get_place_repository] = lambda: repository

    try:
        response = client.get(f"/api/v1/places/{place_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "id": str(place_id),
        "title": "Сысертский электротехнический завод",
        "description": "Советское предприятие в исторических корпусах.",
        "latitude": 56.494711,
        "longitude": 60.809612,
        "created_at": "2026-09-03T20:22:00Z",
        "updated_at": "2026-09-03T20:22:00Z",
    }
    repository.get_by_id.assert_awaited_once_with(place_id)


def test_get_place_returns_404_for_unknown_id() -> None:
    place_id = uuid4()
    repository = AsyncMock(spec=PlaceRepository)
    repository.get_by_id.return_value = None
    app.dependency_overrides[get_place_repository] = lambda: repository

    try:
        response = client.get(f"/api/v1/places/{place_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Place not found"}
    repository.get_by_id.assert_awaited_once_with(place_id)


def test_create_place_returns_created_resource() -> None:
    place_id = uuid4()
    timestamp = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)
    repository = AsyncMock(spec=PlaceRepository)
    repository.create.return_value = PlaceDetailRecord(
        id=place_id,
        title="Завод Красный богатырь",
        description="Историческое здание",
        latitude=55.8031,
        longitude=37.6917,
        created_at=timestamp,
        updated_at=timestamp,
    )
    app.dependency_overrides[get_place_repository] = lambda: repository

    try:
        response = client.post(
            "/api/v1/places",
            json={
                "title": "  Завод Красный богатырь  ",
                "description": "Историческое здание",
                "latitude": 55.8031,
                "longitude": 37.6917,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json() == {
        "id": str(place_id),
        "title": "Завод Красный богатырь",
        "description": "Историческое здание",
        "latitude": 55.8031,
        "longitude": 37.6917,
        "created_at": "2026-09-02T12:00:00Z",
        "updated_at": "2026-09-02T12:00:00Z",
    }
    repository.create.assert_awaited_once_with(
        NewPlace(
            title="Завод Красный богатырь",
            description="Историческое здание",
            latitude=55.8031,
            longitude=37.6917,
        ),
    )


def test_create_place_rejects_blank_title() -> None:
    repository = AsyncMock(spec=PlaceRepository)
    app.dependency_overrides[get_place_repository] = lambda: repository

    try:
        response = client.post(
            "/api/v1/places",
            json={
                "title": "   ",
                "latitude": 55.8031,
                "longitude": 37.6917,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    repository.create.assert_not_awaited()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("latitude", -90.0001),
        ("latitude", 90.0001),
        ("longitude", -180.0001),
        ("longitude", 180.0001),
    ],
)
def test_create_place_rejects_invalid_coordinates(
    field: str,
    value: float,
) -> None:
    repository = AsyncMock(spec=PlaceRepository)
    request_body = {
        "title": "Тестовое место",
        "latitude": 0.0,
        "longitude": 0.0,
    }
    request_body[field] = value
    app.dependency_overrides[get_place_repository] = lambda: repository

    try:
        response = client.post("/api/v1/places", json=request_body)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    repository.create.assert_not_awaited()
