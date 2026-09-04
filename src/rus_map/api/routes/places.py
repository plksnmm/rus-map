from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from rus_map.api.dependencies import (
    MaterialRepositoryDependency,
    PlaceRepositoryDependency,
)
from rus_map.config import get_settings
from rus_map.repositories.place import NewPlace, PlaceDetailRecord
from rus_map.schemas.material import (
    MaterialListResponse,
    MaterialResponse,
    MaterialRevisionResponse,
)
from rus_map.schemas.place import (
    PlaceCreate,
    PlaceDetail,
    PlaceListResponse,
    PlaceSummary,
)

router = APIRouter(prefix="/places", tags=["places"])


def place_detail_response(place: PlaceDetailRecord) -> PlaceDetail:
    """Convert a persistence record into the public detail schema."""
    return PlaceDetail(
        id=place.id,
        title=place.title,
        description=place.description,
        latitude=place.latitude,
        longitude=place.longitude,
        created_at=place.created_at,
        updated_at=place.updated_at,
    )


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

    return place_detail_response(created)


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


@router.get("/{place_id}", response_model=PlaceDetail)
async def get_place(
    place_id: UUID,
    repository: PlaceRepositoryDependency,
) -> PlaceDetail:
    """Return complete information about one place."""
    place = await repository.get_by_id(place_id)

    if place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Place not found",
        )

    return place_detail_response(place)


@router.get("/{place_id}/materials", response_model=MaterialListResponse)
async def list_place_materials(
    place_id: UUID,
    repository: MaterialRepositoryDependency,
) -> MaterialListResponse:
    """Return published materials for one existing place."""
    page = await repository.list_published_for_place(place_id)

    if page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Place not found",
        )

    return MaterialListResponse(
        items=[
            MaterialResponse(
                id=material.id,
                type=material.type,
                title=material.title,
                source=material.source,
                revision=MaterialRevisionResponse(
                    revision_number=material.revision_number,
                    content=material.content,
                    url=material.url,
                    media_id=material.media_asset_id,
                    created_at=material.revision_created_at,
                ),
                created_at=material.created_at,
                updated_at=material.updated_at,
            )
            for material in page.items
        ],
        total=page.total,
    )


@router.get("/{place_id}/images/{media_id}", response_class=FileResponse)
async def get_place_image(
    place_id: UUID,
    media_id: UUID,
    repository: MaterialRepositoryDependency,
) -> FileResponse:
    """Return an optimized image exposed by a published place material."""
    image = await repository.get_published_image(place_id, media_id)
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )

    media_root = get_settings().media_root.resolve()
    image_path = (media_root / image.storage_key).resolve()
    if not image_path.is_relative_to(media_root) or not image_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )

    return FileResponse(
        path=Path(image_path),
        media_type=image.content_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
