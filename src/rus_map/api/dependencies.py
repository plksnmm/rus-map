from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from rus_map.db.session import get_session
from rus_map.repositories.place import PlaceRepository

SessionDependency = Annotated[AsyncSession, Depends(get_session)]


def get_place_repository(session: SessionDependency) -> PlaceRepository:
    """Build a place repository for the current database session."""
    return PlaceRepository(session)


PlaceRepositoryDependency = Annotated[
    PlaceRepository,
    Depends(get_place_repository),
]
