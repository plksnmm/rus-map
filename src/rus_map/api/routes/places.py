from fastapi import APIRouter, status

from rus_map.api.dependencies import PlaceRepositoryDependency
from rus_map.repositories.place import NewPlace
from rus_map.schemas.place import (
    PlaceCreate,
    PlaceDetail,
    PlaceListResponse,
    PlaceSummary,
)

router = APIRouter(prefix="/places", tags=["places"])


@router.post(
    "",
    response_model=PlaceDetail,
    status_code=status.HTTP_201_CREATED,
)
async def create_place(
    place: PlaceCreate,
    repository: PlaceRepositoryDependency,
) -> PlaceDetail:
    """Create a place on the map."""
    created = await repository.create(
        NewPlace(
            title=place.title,
            description=place.description,
            latitude=place.latitude,
            longitude=place.longitude,
        ),
    )

    return PlaceDetail(
        id=created.id,
        title=created.title,
        description=created.description,
        latitude=created.latitude,
        longitude=created.longitude,
        created_at=created.created_at,
        updated_at=created.updated_at,
    )


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
