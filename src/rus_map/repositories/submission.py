from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from rus_map.models import PlaceSubmission, SubmissionStatus


@dataclass(frozen=True, slots=True)
class NewPlaceSubmission:
    """Validated proposal ready for persistence."""

    title: str
    description: str | None
    latitude: float
    longitude: float
    source_urls: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PlaceSubmissionRecord:
    """Complete proposal state returned by the persistence layer."""

    id: UUID
    status: SubmissionStatus
    title: str
    description: str | None
    latitude: float
    longitude: float
    source_urls: tuple[str, ...]
    review_notes: str | None
    approved_place_id: UUID | None
    moderated_by_admin_id: UUID | None
    moderated_at: datetime | None
    created_at: datetime
    updated_at: datetime


type SubmissionRow = tuple[
    UUID,
    SubmissionStatus,
    str,
    str | None,
    float,
    float,
    list[str],
    str | None,
    UUID | None,
    UUID | None,
    datetime | None,
    datetime,
    datetime,
]


SUBMISSION_COLUMNS = (
    PlaceSubmission.id,
    PlaceSubmission.status,
    PlaceSubmission.title,
    PlaceSubmission.description,
    PlaceSubmission.latitude,
    PlaceSubmission.longitude,
    PlaceSubmission.source_urls,
    PlaceSubmission.review_notes,
    PlaceSubmission.approved_place_id,
    PlaceSubmission.moderated_by_admin_id,
    PlaceSubmission.moderated_at,
    PlaceSubmission.created_at,
    PlaceSubmission.updated_at,
)


def submission_record(row: SubmissionRow) -> PlaceSubmissionRecord:
    """Convert a selected database row into an immutable record."""
    return PlaceSubmissionRecord(
        id=row[0],
        status=row[1],
        title=row[2],
        description=row[3],
        latitude=row[4],
        longitude=row[5],
        source_urls=tuple(row[6]),
        review_notes=row[7],
        approved_place_id=row[8],
        moderated_by_admin_id=row[9],
        moderated_at=row[10],
        created_at=row[11],
        updated_at=row[12],
    )


class PlaceSubmissionRepository:
    """Persist proposed places without exposing them through public queries."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, proposal: NewPlaceSubmission) -> PlaceSubmissionRecord:
        """Insert one pending proposal."""
        statement = (
            insert(PlaceSubmission)
            .values(
                id=uuid4(),
                status=SubmissionStatus.PENDING,
                title=proposal.title,
                description=proposal.description,
                latitude=proposal.latitude,
                longitude=proposal.longitude,
                source_urls=list(proposal.source_urls),
            )
            .returning(*SUBMISSION_COLUMNS)
        )
        row = (await self._session.execute(statement)).tuples().one()
        return submission_record(row)

    async def get_for_update(
        self,
        submission_id: UUID,
    ) -> PlaceSubmissionRecord | None:
        """Lock one proposal so concurrent decisions cannot create duplicates."""
        statement = (
            select(*SUBMISSION_COLUMNS)
            .where(PlaceSubmission.id == submission_id)
            .with_for_update()
        )
        row = (await self._session.execute(statement)).tuples().one_or_none()
        return None if row is None else submission_record(row)

    async def get(self, submission_id: UUID) -> PlaceSubmissionRecord | None:
        """Return one proposal without locking it."""
        statement = select(*SUBMISSION_COLUMNS).where(
            PlaceSubmission.id == submission_id
        )
        row = (await self._session.execute(statement)).tuples().one_or_none()
        return None if row is None else submission_record(row)

    async def list(
        self,
        status: SubmissionStatus | None,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[PlaceSubmissionRecord], int]:
        """Return a stable page and the total number matching its filter."""
        filters = () if status is None else (PlaceSubmission.status == status,)
        count_statement = (
            select(func.count()).select_from(PlaceSubmission).where(*filters)
        )
        page_statement = (
            select(*SUBMISSION_COLUMNS)
            .where(*filters)
            .order_by(PlaceSubmission.created_at.asc(), PlaceSubmission.id.asc())
            .limit(limit)
            .offset(offset)
        )
        total = int((await self._session.scalar(count_statement)) or 0)
        rows = (await self._session.execute(page_statement)).tuples().all()
        return [submission_record(row) for row in rows], total

    async def mark_approved(
        self,
        submission_id: UUID,
        place_id: UUID,
        admin_id: UUID,
        review_notes: str | None,
    ) -> PlaceSubmissionRecord | None:
        """Record the single place created from a still-pending proposal."""
        statement = (
            update(PlaceSubmission)
            .where(
                PlaceSubmission.id == submission_id,
                PlaceSubmission.status == SubmissionStatus.PENDING,
            )
            .values(
                status=SubmissionStatus.APPROVED,
                approved_place_id=place_id,
                moderated_by_admin_id=admin_id,
                review_notes=review_notes,
                moderated_at=datetime.now(UTC),
            )
            .returning(*SUBMISSION_COLUMNS)
        )
        row = (await self._session.execute(statement)).tuples().one_or_none()
        return None if row is None else submission_record(row)

    async def mark_rejected(
        self,
        submission_id: UUID,
        admin_id: UUID,
        review_notes: str | None,
    ) -> PlaceSubmissionRecord | None:
        """Reject a still-pending proposal without deleting its audit record."""
        statement = (
            update(PlaceSubmission)
            .where(
                PlaceSubmission.id == submission_id,
                PlaceSubmission.status == SubmissionStatus.PENDING,
            )
            .values(
                status=SubmissionStatus.REJECTED,
                moderated_by_admin_id=admin_id,
                review_notes=review_notes,
                moderated_at=datetime.now(UTC),
            )
            .returning(*SUBMISSION_COLUMNS)
        )
        row = (await self._session.execute(statement)).tuples().one_or_none()
        return None if row is None else submission_record(row)
