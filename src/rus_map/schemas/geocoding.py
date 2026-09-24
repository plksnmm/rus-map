from pydantic import BaseModel, Field


class GeocodingResult(BaseModel):
    """One safe, normalized address match returned to the browser."""

    display_name: str = Field(min_length=1, max_length=500)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    bounding_box: tuple[float, float, float, float] | None = None


class GeocodingSearchResponse(BaseModel):
    """Address matches with the attribution required by the provider."""

    items: list[GeocodingResult]
    attribution: str = "© OpenStreetMap contributors"
    attribution_url: str = "https://www.openstreetmap.org/copyright"
