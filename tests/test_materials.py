from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient

from rus_map.api.dependencies import get_material_repository
from rus_map.main import app
from rus_map.models import MaterialType
from rus_map.repositories.material import (
    MaterialPage,
    MaterialRecord,
    MaterialRepository,
)

client = TestClient(app)


def test_list_materials_returns_latest_published_revision() -> None:
    place_id = uuid4()
    material_id = uuid4()
    timestamp = datetime(2026, 9, 4, 9, 0, tzinfo=UTC)
    repository = AsyncMock(spec=MaterialRepository)
    repository.list_published_for_place.return_value = MaterialPage(
        items=[
            MaterialRecord(
                id=material_id,
                type=MaterialType.EXTERNAL_LINK,
                title="Репортаж о заводе",
                source="Русь пролетарская",
                revision_number=2,
                content=None,
                url="https://example.com/report",
                revision_created_at=timestamp,
                created_at=timestamp,
                updated_at=timestamp,
            ),
        ],
        total=1,
    )
    app.dependency_overrides[get_material_repository] = lambda: repository

    try:
        response = client.get(f"/api/v1/places/{place_id}/materials")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": str(material_id),
                "type": "external_link",
                "title": "Репортаж о заводе",
                "source": "Русь пролетарская",
                "revision": {
                    "revision_number": 2,
                    "content": None,
                    "url": "https://example.com/report",
                    "created_at": "2026-09-04T09:00:00Z",
                },
                "created_at": "2026-09-04T09:00:00Z",
                "updated_at": "2026-09-04T09:00:00Z",
            },
        ],
        "total": 1,
    }
    repository.list_published_for_place.assert_awaited_once_with(place_id)


def test_list_materials_returns_empty_collection() -> None:
    place_id = uuid4()
    repository = AsyncMock(spec=MaterialRepository)
    repository.list_published_for_place.return_value = MaterialPage(
        items=[],
        total=0,
    )
    app.dependency_overrides[get_material_repository] = lambda: repository

    try:
        response = client.get(f"/api/v1/places/{place_id}/materials")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_list_materials_returns_404_for_unknown_place() -> None:
    place_id = uuid4()
    repository = AsyncMock(spec=MaterialRepository)
    repository.list_published_for_place.return_value = None
    app.dependency_overrides[get_material_repository] = lambda: repository

    try:
        response = client.get(f"/api/v1/places/{place_id}/materials")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Place not found"}
