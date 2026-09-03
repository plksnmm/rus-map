from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Float, func, insert, select
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
class NewPlace:
    """Validated place data ready to be persisted."""

    title: str
    description: str | None
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class PlaceDetailRecord:
    """Complete place data returned after persistence."""

    id: UUID
    title: str
    description: str | None
    latitude: float
    longitude: float
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class PlacePage:
    """A collection of places and its total size."""

    items: list[PlaceRecord]
    total: int


class PlaceRepository:
    """Persist places without depending on the HTTP layer."""

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

    async def get_by_id(self, place_id: UUID) -> PlaceDetailRecord | None:
        """Return one place or None when the identifier does not exist."""
        statement = select(
            Place.id,
            Place.title,
            Place.description,
            func.ST_Y(Place.location, type_=Float).label("latitude"),
            func.ST_X(Place.location, type_=Float).label("longitude"),
            Place.created_at,
            Place.updated_at,
        ).where(Place.id == place_id)
        row = (await self._session.execute(statement)).tuples().one_or_none()

        if row is None:
            return None

        return PlaceDetailRecord(
            id=row[0],
            title=row[1],
            description=row[2],
            latitude=row[3],
            longitude=row[4],
            created_at=row[5],
            updated_at=row[6],
        )

    async def create(self, new_place: NewPlace) -> PlaceDetailRecord:
        """Insert a place and return its database-generated values."""
        statement = (
            insert(Place)
            .values(
                id=uuid4(),
                title=new_place.title,
                description=new_place.description,
                location=func.ST_SetSRID(
                    func.ST_MakePoint(
                        new_place.longitude,
                        new_place.latitude,
                    ),
                    4326,
                ),
            )
            .returning(
                Place.id,
                Place.title,
                Place.description,
                func.ST_Y(Place.location, type_=Float).label("latitude"),
                func.ST_X(Place.location, type_=Float).label("longitude"),
                Place.created_at,
                Place.updated_at,
            )
        )
        row = (await self._session.execute(statement)).tuples().one()

        return PlaceDetailRecord(
            id=row[0],
            title=row[1],
            description=row[2],
            latitude=row[3],
            longitude=row[4],
            created_at=row[5],
            updated_at=row[6],
        )
