from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status

from rus_map.api.dependencies import GeocodingServiceDependency
from rus_map.schemas.geocoding import GeocodingSearchResponse
from rus_map.services.geocoding import GeocodingRateLimited, GeocodingUnavailable

router = APIRouter(prefix="/geocoding", tags=["geocoding"])


@router.get("/search", response_model=GeocodingSearchResponse)
async def search_address(
    response: Response,
    service: GeocodingServiceDependency,
    query: Annotated[str, Query(alias="q", min_length=3, max_length=300)],
) -> GeocodingSearchResponse:
    """Resolve one user-entered Russian address without autocomplete."""
    cleaned_query = " ".join(query.split())
    if len(cleaned_query) < 3:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Address query is too short",
        )
    try:
        items = await service.search(cleaned_query)
    except GeocodingRateLimited as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Address search is temporarily busy",
            headers={"Retry-After": "1"},
        ) from error
    except GeocodingUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Address search is unavailable",
        ) from error
    response.headers["Cache-Control"] = "private, max-age=3600"
    return GeocodingSearchResponse(items=items)
