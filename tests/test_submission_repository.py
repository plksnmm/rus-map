from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from rus_map.models import SubmissionStatus
from rus_map.repositories.submission import (
    NewPlaceSubmission,
    PlaceSubmissionRepository,
)


def submission_row(
    *,
    status: SubmissionStatus = SubmissionStatus.PENDING,
    approved_place_id: UUID | None = None,
) -> tuple[object, ...]:
    timestamp = datetime.now(UTC)
    return (
        uuid4(),
        status,
        "Завод Красный богатырь",
        "Историческое предприятие",
        55.8031,
        37.6917,
        ["https://example.com/factory"],
        None,
        approved_place_id,
        timestamp if status is not SubmissionStatus.PENDING else None,
        timestamp,
        timestamp,
    )


def execute_result_with(row: tuple[object, ...] | None) -> Mock:
    tuples = Mock()
    tuples.one.return_value = row
    tuples.one_or_none.return_value = row
    result = Mock()
    result.tuples.return_value = tuples
    return result


@pytest.mark.asyncio
async def test_create_inserts_pending_submission_without_place() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = execute_result_with(submission_row())
    repository = PlaceSubmissionRepository(session)

    created = await repository.create(
        NewPlaceSubmission(
            title="Завод Красный богатырь",
            description="Историческое предприятие",
            latitude=55.8031,
            longitude=37.6917,
            source_urls=("https://example.com/factory",),
        )
    )

    assert created.status is SubmissionStatus.PENDING
    assert created.approved_place_id is None
    statement = session.execute.await_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "INSERT INTO app.place_submissions" in sql
    assert "app.places" not in sql


@pytest.mark.asyncio
async def test_get_for_update_locks_submission() -> None:
    session = AsyncMock(spec=AsyncSession)
    row = submission_row()
    session.execute.return_value = execute_result_with(row)
    submission_id = row[0]

    found = await PlaceSubmissionRepository(session).get_for_update(submission_id)

    assert found is not None
    statement = session.execute.await_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in sql


@pytest.mark.asyncio
async def test_mark_approved_updates_only_pending_submission() -> None:
    session = AsyncMock(spec=AsyncSession)
    place_id = uuid4()
    session.execute.return_value = execute_result_with(
        submission_row(status=SubmissionStatus.APPROVED, approved_place_id=place_id)
    )

    approved = await PlaceSubmissionRepository(session).mark_approved(
        uuid4(),
        place_id,
        "Проверено",
    )

    assert approved is not None
    assert approved.approved_place_id == place_id
    statement = session.execute.await_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "UPDATE app.place_submissions" in sql
    assert "place_submissions.status =" in sql
    assert "RETURNING" in sql


@pytest.mark.asyncio
async def test_mark_rejected_does_not_create_place() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = execute_result_with(
        submission_row(status=SubmissionStatus.REJECTED)
    )

    rejected = await PlaceSubmissionRepository(session).mark_rejected(
        uuid4(),
        "Недостаточно источников",
    )

    assert rejected is not None
    assert rejected.status is SubmissionStatus.REJECTED
    statement = session.execute.await_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "UPDATE app.place_submissions" in sql
    assert "app.places" not in sql
