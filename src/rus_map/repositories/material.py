from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rus_map.models import (
    Material,
    MaterialRevision,
    MaterialType,
    ModerationStatus,
    Place,
)


@dataclass(frozen=True, slots=True)
class MaterialRecord:
    """One published material with its latest revision."""

    id: UUID
    type: MaterialType
    title: str
    source: str | None
    revision_number: int
    content: str | None
    url: str | None
    revision_created_at: datetime
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class MaterialPage:
    """Published materials for an existing place."""

    items: list[MaterialRecord]
    total: int


class MaterialRepository:
    """Read versioned place materials without depending on HTTP."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_published_for_place(
        self,
        place_id: UUID,
    ) -> MaterialPage | None:
        """Return published materials, or None when the place does not exist."""
        existing_place_id = await self._session.scalar(
            select(Place.id).where(Place.id == place_id),
        )
        if existing_place_id is None:
            return None

        ranked_revisions = (
            select(
                MaterialRevision.material_id,
                MaterialRevision.revision_number,
                MaterialRevision.content,
                MaterialRevision.url,
                MaterialRevision.created_at.label("revision_created_at"),
                func.row_number()
                .over(
                    partition_by=MaterialRevision.material_id,
                    order_by=(
                        MaterialRevision.revision_number.desc(),
                        MaterialRevision.created_at.desc(),
                        MaterialRevision.id.desc(),
                    ),
                )
                .label("revision_rank"),
            )
            .where(MaterialRevision.status == ModerationStatus.PUBLISHED)
            .subquery()
        )
        statement = (
            select(
                Material.id,
                Material.type,
                Material.title,
                Material.source,
                ranked_revisions.c.revision_number,
                ranked_revisions.c.content,
                ranked_revisions.c.url,
                ranked_revisions.c.revision_created_at,
                Material.created_at,
                Material.updated_at,
            )
            .join(
                ranked_revisions,
                ranked_revisions.c.material_id == Material.id,
            )
            .where(
                Material.place_id == place_id,
                Material.status == ModerationStatus.PUBLISHED,
                ranked_revisions.c.revision_rank == 1,
            )
            .order_by(Material.created_at, Material.id)
        )
        rows = (await self._session.execute(statement)).tuples().all()
        items = [
            MaterialRecord(
                id=row[0],
                type=row[1],
                title=row[2],
                source=row[3],
                revision_number=row[4],
                content=row[5],
                url=row[6],
                revision_created_at=row[7],
                created_at=row[8],
                updated_at=row[9],
            )
            for row in rows
        ]

        return MaterialPage(items=items, total=len(items))
