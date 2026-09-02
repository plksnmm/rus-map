from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient

from rus_map.api.dependencies import get_place_repository
from rus_map.main import app
from rus_map.repositories.place import PlacePage, PlaceRecord, PlaceRepository

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
