from uuid import UUID

import pytest
from pydantic import ValidationError

from rus_map.admin.material_import import PlaceMaterialsManifest
from rus_map.models import ModerationStatus

PLACE_ID = "11111111-1111-4111-8111-111111111111"
MATERIAL_ID = "22222222-2222-4222-8222-222222222222"
REVISION_ID = "33333333-3333-4333-8333-333333333333"


def manifest_data() -> dict[str, object]:
    return {
        "schema_version": 1,
        "place_id": PLACE_ID,
        "materials": [
            {
                "id": MATERIAL_ID,
                "type": "text",
                "title": "История завода",
                "source": "Русь пролетарская",
                "revisions": [
                    {
                        "id": REVISION_ID,
                        "revision_number": 1,
                        "content": "Первая проверяемая редакция.",
                    },
                ],
            },
        ],
    }


def test_manifest_defaults_to_pending_review() -> None:
    manifest = PlaceMaterialsManifest.model_validate(manifest_data())

    assert manifest.place_id == UUID(PLACE_ID)
    assert manifest.materials[0].status is ModerationStatus.PENDING_REVIEW
    assert manifest.materials[0].revisions[0].status is ModerationStatus.PENDING_REVIEW


def test_manifest_accepts_explicit_published_status() -> None:
    data = manifest_data()
    material = data["materials"][0]  # type: ignore[index]
    material["status"] = "published"  # type: ignore[index]
    material["revisions"][0]["status"] = "published"  # type: ignore[index]

    manifest = PlaceMaterialsManifest.model_validate(data)

    assert manifest.materials[0].status is ModerationStatus.PUBLISHED
    assert manifest.materials[0].revisions[0].status is ModerationStatus.PUBLISHED


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "data:text/plain,danger",
        "https:///missing-host",
    ],
)
def test_manifest_rejects_unsafe_or_incomplete_urls(url: str) -> None:
    data = manifest_data()
    material = data["materials"][0]  # type: ignore[index]
    material["type"] = "video"  # type: ignore[index]
    revision = material["revisions"][0]  # type: ignore[index]
    revision["content"] = None
    revision["url"] = url

    with pytest.raises(ValidationError):
        PlaceMaterialsManifest.model_validate(data)


def test_manifest_rejects_text_material_with_url() -> None:
    data = manifest_data()
    revision = data["materials"][0]["revisions"][0]  # type: ignore[index]
    revision["content"] = None
    revision["url"] = "https://example.com/report"

    with pytest.raises(ValidationError, match="text material"):
        PlaceMaterialsManifest.model_validate(data)


def test_manifest_rejects_duplicate_revision_numbers() -> None:
    data = manifest_data()
    revisions = data["materials"][0]["revisions"]  # type: ignore[index]
    revisions.append(
        {
            "id": "44444444-4444-4444-8444-444444444444",
            "revision_number": 1,
            "content": "Другая редакция с тем же номером.",
        },
    )

    with pytest.raises(ValidationError, match="revision numbers must be unique"):
        PlaceMaterialsManifest.model_validate(data)


def test_manifest_rejects_unknown_fields() -> None:
    data = manifest_data()
    data["password"] = "must never be accepted"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PlaceMaterialsManifest.model_validate(data)
