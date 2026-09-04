from uuid import UUID

import pytest
from pydantic import ValidationError

from rus_map.admin.place_import import PlacesManifest

PLACE_ID = "11111111-1111-4111-8111-111111111111"


def manifest_data() -> dict[str, object]:
    return {
        "schema_version": 1,
        "places": [
            {
                "id": PLACE_ID,
                "title": "Кусковский химический завод",
                "description": "Проверенная историческая справка.",
                "latitude": 55.74,
                "longitude": 37.75,
            },
        ],
    }


def test_manifest_accepts_valid_place() -> None:
    manifest = PlacesManifest.model_validate(manifest_data())

    assert manifest.schema_version == 1
    assert manifest.places[0].id == UUID(PLACE_ID)
    assert manifest.places[0].title == "Кусковский химический завод"
    assert manifest.places[0].latitude == 55.74
    assert manifest.places[0].longitude == 37.75


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("latitude", -90.0001),
        ("latitude", 90.0001),
        ("longitude", -180.0001),
        ("longitude", 180.0001),
    ],
)
def test_manifest_rejects_coordinates_outside_earth(
    field: str,
    value: float,
) -> None:
    data = manifest_data()
    place = data["places"][0]  # type: ignore[index]
    place[field] = value

    with pytest.raises(ValidationError):
        PlacesManifest.model_validate(data)


def test_manifest_rejects_duplicate_place_ids() -> None:
    data = manifest_data()
    places = data["places"]  # type: ignore[assignment]
    places.append(
        {
            "id": PLACE_ID,
            "title": "Дубликат",
            "description": None,
            "latitude": 55.8,
            "longitude": 37.8,
        },
    )

    with pytest.raises(ValidationError, match="place IDs must be unique"):
        PlacesManifest.model_validate(data)


def test_manifest_rejects_unknown_fields() -> None:
    data = manifest_data()
    data["token"] = "must never be accepted"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PlacesManifest.model_validate(data)
