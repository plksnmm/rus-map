from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Float, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rus_map.models import Place


@dataclass(frozen=True, slots=True)
class PlaceRecord:
    """Place data returned by the persistence layer."""

    id: UUID
    title: str
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class PlacePage:
    """A collection of places and its total size."""

    items: list[PlaceRecord]
    total: int


class PlaceRepository:
    """Read places from PostgreSQL without depending on the HTTP layer."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self) -> PlacePage:
        """Return all places in a deterministic order."""
        statement = (
            select(
                Place.id,
                Place.title,
                func.ST_Y(Place.location, type_=Float).label("latitude"),
                func.ST_X(Place.location, type_=Float).label("longitude"),
                func.count().over().label("total"),
            )
            .select_from(Place)
            .order_by(Place.created_at, Place.id)
        )
        rows = (await self._session.execute(statement)).tuples().all()

        items = [
            PlaceRecord(
                id=place_id,
                title=title,
                latitude=latitude,
                longitude=longitude,
            )
            for place_id, title, latitude, longitude, _ in rows
        ]
        total = rows[0][4] if rows else 0

        return PlacePage(items=items, total=total)
