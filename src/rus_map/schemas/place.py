from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

PlaceTitle = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=200,
    ),
]
Latitude = Annotated[float, Field(ge=-90, le=90)]
Longitude = Annotated[float, Field(ge=-180, le=180)]
PlaceDescription = Annotated[str, Field(max_length=10_000)]


class PlaceCreate(BaseModel):
    """Data required to create a place."""

    title: PlaceTitle
    description: PlaceDescription | None = None
    latitude: Latitude
    longitude: Longitude


class PlaceSummary(BaseModel):
    """Short representation of a place displayed on the map."""

    id: UUID
    title: PlaceTitle
    latitude: Latitude
    longitude: Longitude


class PlaceDetail(PlaceCreate):
    """Complete public representation of a stored place."""

    id: UUID
    created_at: datetime
    updated_at: datetime


class PlaceListResponse(BaseModel):
    """Paginated collection of places."""

    items: list[PlaceSummary]
    total: int = Field(ge=0)
