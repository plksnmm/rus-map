from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from rus_map.schemas.place import PlaceCreate, PlaceDetail


def test_place_create_normalizes_title() -> None:
    place = PlaceCreate(
        title="  Завод Красный богатырь  ",
        description="Историческое здание",
        latitude=55.8031,
        longitude=37.6917,
    )

    assert place.title == "Завод Красный богатырь"
    assert place.description == "Историческое здание"


@pytest.mark.parametrize("title", ["", " ", "\t\n"])
def test_place_create_rejects_blank_title(title: str) -> None:
    with pytest.raises(ValidationError):
        PlaceCreate(
            title=title,
            latitude=55.8031,
            longitude=37.6917,
        )


def test_place_create_rejects_too_long_description() -> None:
    with pytest.raises(ValidationError):
        PlaceCreate(
            title="Тестовое место",
            description="x" * 10_001,
            latitude=55.8031,
            longitude=37.6917,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("latitude", -90.0001),
        ("latitude", 90.0001),
        ("longitude", -180.0001),
        ("longitude", 180.0001),
    ],
)
def test_place_create_rejects_invalid_coordinates(
    field: str,
    value: float,
) -> None:
    place_data: dict[str, object] = {
        "title": "Тестовое место",
        "latitude": 0.0,
        "longitude": 0.0,
    }
    place_data[field] = value

    with pytest.raises(ValidationError):
        PlaceCreate.model_validate(place_data)


def test_place_detail_contains_generated_fields() -> None:
    timestamp = datetime.now(UTC)

    place = PlaceDetail(
        id=uuid4(),
        title="Тестовое место",
        description=None,
        latitude=55.8031,
        longitude=37.6917,
        created_at=timestamp,
        updated_at=timestamp,
    )

    assert place.created_at.tzinfo is not None
    assert place.updated_at == place.created_at
