from uuid import UUID

from pydantic import BaseModel, Field


class PlaceSummary(BaseModel):
    """Short representation of a place displayed on the map."""

    id: UUID
    title: str = Field(min_length=1, max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class PlaceListResponse(BaseModel):
    """Paginated collection of places."""

    items: list[PlaceSummary]
    total: int = Field(ge=0)
