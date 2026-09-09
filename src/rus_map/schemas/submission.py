import re
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    field_validator,
)

from rus_map.models import SubmissionStatus
from rus_map.schemas.place import Latitude, Longitude, PlaceDescription, PlaceTitle

MAX_SOURCE_URLS = 10
HTML_TAG_PATTERN = re.compile(r"<\s*/?\s*[a-zA-Z][^>]*>")

SubmissionReviewNotes = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=5_000),
]


def reject_html(value: str | None) -> str | None:
    """Reject tag-shaped input; submission text is always plain text."""
    if value is not None and HTML_TAG_PATTERN.search(value):
        raise ValueError("HTML is not allowed")
    return value


class PlaceSubmissionCreate(BaseModel):
    """Validated public data for a proposed place."""

    model_config = ConfigDict(extra="forbid")

    title: PlaceTitle
    description: PlaceDescription | None = None
    latitude: Latitude
    longitude: Longitude
    source_urls: list[HttpUrl] = Field(default_factory=list, max_length=MAX_SOURCE_URLS)

    _plain_title = field_validator("title")(reject_html)
    _plain_description = field_validator("description")(reject_html)

    @field_validator("source_urls")
    @classmethod
    def source_urls_are_unique(cls, urls: list[HttpUrl]) -> list[HttpUrl]:
        if len({str(url) for url in urls}) != len(urls):
            raise ValueError("source URLs must be unique")
        return urls


class PlaceSubmissionDecision(BaseModel):
    """Optional internal note attached to a moderation decision."""

    model_config = ConfigDict(extra="forbid")

    review_notes: SubmissionReviewNotes | None = None

    _plain_review_notes = field_validator("review_notes")(reject_html)


class PlaceSubmissionResponse(BaseModel):
    """Complete proposal state returned only to administrators."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: SubmissionStatus
    title: str
    description: str | None
    latitude: float
    longitude: float
    source_urls: list[str]
    review_notes: str | None
    approved_place_id: UUID | None
    moderated_by_admin_id: UUID | None
    moderated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PlaceSubmissionListResponse(BaseModel):
    """Paginated administrative submission queue."""

    items: list[PlaceSubmissionResponse]
    total: int
    limit: int
    offset: int
