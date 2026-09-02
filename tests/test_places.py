from fastapi.testclient import TestClient

from rus_map.main import app

client = TestClient(app)


def test_list_places_returns_empty_collection() -> None:
    response = client.get("/api/v1/places")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
    }
