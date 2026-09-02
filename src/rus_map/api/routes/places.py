from fastapi import APIRouter

from rus_map.api.dependencies import PlaceRepositoryDependency
from rus_map.schemas.place import PlaceListResponse, PlaceSummary

router = APIRouter(prefix="/places", tags=["places"])


@router.get("", response_model=PlaceListResponse)
async def list_places(
    repository: PlaceRepositoryDependency,
) -> PlaceListResponse:
    """Return places available for displaying on the map."""
    page = await repository.list()

    return PlaceListResponse(
        items=[
            PlaceSummary(
                id=place.id,
                title=place.title,
                latitude=place.latitude,
                longitude=place.longitude,
            )
            for place in page.items
        ],
        total=page.total,
    )
