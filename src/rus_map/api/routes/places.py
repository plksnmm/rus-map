from fastapi import APIRouter

from rus_map.schemas.place import PlaceListResponse

router = APIRouter(prefix="/places", tags=["places"])


@router.get("", response_model=PlaceListResponse)
async def list_places() -> PlaceListResponse:
    """Return places available for displaying on the map."""
    return PlaceListResponse(items=[], total=0)
