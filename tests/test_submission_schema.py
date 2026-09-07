import pytest
from pydantic import ValidationError

from rus_map.schemas.submission import (
    MAX_SOURCE_URLS,
    PlaceSubmissionCreate,
    PlaceSubmissionDecision,
)


def valid_submission(**overrides: object) -> PlaceSubmissionCreate:
    data: dict[str, object] = {
        "title": "Завод Красный богатырь",
        "description": "Предлагаю проверить историческое предприятие.",
        "latitude": 55.8031,
        "longitude": 37.6917,
        "source_urls": ["https://example.com/factory"],
    }
    data.update(overrides)
    return PlaceSubmissionCreate.model_validate(data)


def test_submission_accepts_plain_text_and_https_sources() -> None:
    submission = valid_submission()

    assert submission.title == "Завод Красный богатырь"
    assert str(submission.source_urls[0]) == "https://example.com/factory"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", "<strong>Завод</strong>"),
        ("description", "Описание <script>alert(1)</script>"),
    ],
)
def test_submission_rejects_html(field: str, value: str) -> None:
    with pytest.raises(ValidationError, match="HTML is not allowed"):
        valid_submission(**{field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("latitude", -90.01),
        ("latitude", 90.01),
        ("longitude", -180.01),
        ("longitude", 180.01),
    ],
)
def test_submission_rejects_coordinates_outside_earth(
    field: str,
    value: float,
) -> None:
    with pytest.raises(ValidationError):
        valid_submission(**{field: value})


def test_submission_rejects_non_http_and_duplicate_sources() -> None:
    with pytest.raises(ValidationError):
        valid_submission(source_urls=["javascript:alert(1)"])

    with pytest.raises(ValidationError, match="source URLs must be unique"):
        valid_submission(
            source_urls=["https://example.com", "https://example.com/"],
        )


def test_submission_limits_sources_and_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        valid_submission(
            source_urls=[
                f"https://example.com/{index}" for index in range(MAX_SOURCE_URLS + 1)
            ]
        )

    with pytest.raises(ValidationError):
        valid_submission(unexpected="value")


def test_review_notes_are_plain_text() -> None:
    decision = PlaceSubmissionDecision(review_notes="Проверено по архиву")

    assert decision.review_notes == "Проверено по архиву"
    with pytest.raises(ValidationError, match="HTML is not allowed"):
        PlaceSubmissionDecision(review_notes="<b>Одобрить</b>")
