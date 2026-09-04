from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from rus_map.models import MaterialType
from rus_map.schemas.material import MaterialRevisionResponse


def test_revision_accepts_https_url() -> None:
    revision = MaterialRevisionResponse(
        revision_number=1,
        content=None,
        url="https://example.com/report",
        created_at=datetime.now(UTC),
    )

    assert revision.url == "https://example.com/report"


@pytest.mark.parametrize("url", ["ftp://example.com/file", "javascript:alert(1)"])
def test_revision_rejects_unsupported_url(url: str) -> None:
    with pytest.raises(ValidationError):
        MaterialRevisionResponse(
            revision_number=1,
            content=None,
            url=url,
            created_at=datetime.now(UTC),
        )


@pytest.mark.parametrize(
    ("content", "url"),
    [
        (None, None),
        ("Текст", "https://example.com"),
    ],
)
def test_revision_requires_exactly_one_value(
    content: str | None,
    url: str | None,
) -> None:
    with pytest.raises(ValidationError):
        MaterialRevisionResponse(
            revision_number=1,
            content=content,
            url=url,
            created_at=datetime.now(UTC),
        )


def test_material_type_values_are_stable() -> None:
    assert [material_type.value for material_type in MaterialType] == [
        "text",
        "external_link",
        "image",
        "video",
        "audio",
    ]
