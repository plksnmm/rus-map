from uuid import uuid4

import pytest
from pydantic import ValidationError

from rus_map.schemas.place import PlaceSummary


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("latitude", -90.0001),
        ("latitude", 90.0001),
        ("longitude", -180.0001),
        ("longitude", 180.0001),
    ],
)
def test_place_summary_rejects_invalid_coordinates(
    field: str,
    value: float,
) -> None:
    place_data: dict[str, object] = {
        "id": uuid4(),
        "title": "Тестовое место",
        "latitude": 0.0,
        "longitude": 0.0,
    }
    place_data[field] = value

    with pytest.raises(ValidationError):
        PlaceSummary.model_validate(place_data)


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        (-90.0, -180.0),
        (90.0, 180.0),
    ],
)
def test_place_summary_accepts_boundary_coordinates(
    latitude: float,
    longitude: float,
) -> None:
    place = PlaceSummary(
        id=uuid4(),
        title="Тестовое место",
        latitude=latitude,
        longitude=longitude,
    )

    assert place.latitude == latitude
    assert place.longitude == longitude
