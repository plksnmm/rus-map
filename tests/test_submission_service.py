from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from rus_map.models import SubmissionStatus
from rus_map.repositories.place import PlaceDetailRecord
from rus_map.repositories.submission import (
    NewPlaceSubmission,
    PlaceSubmissionRecord,
)
from rus_map.services.submission import (
    InvalidSubmissionTransition,
    PlaceSubmissionService,
    SubmissionNotFound,
)


def submission_record(
    status: SubmissionStatus,
    *,
    submission_id: UUID | None = None,
    approved_place_id: UUID | None = None,
) -> PlaceSubmissionRecord:
    timestamp = datetime.now(UTC)
    return PlaceSubmissionRecord(
        id=submission_id or uuid4(),
        status=status,
        title="Завод Красный богатырь",
        description="Историческое предприятие",
        latitude=55.8031,
        longitude=37.6917,
        source_urls=("https://example.com/factory",),
        review_notes=None,
        approved_place_id=approved_place_id,
        moderated_at=None if status is SubmissionStatus.PENDING else timestamp,
        created_at=timestamp,
        updated_at=timestamp,
    )


def place_record(place_id: UUID) -> PlaceDetailRecord:
    timestamp = datetime.now(UTC)
    return PlaceDetailRecord(
        id=place_id,
        title="Завод Красный богатырь",
        description="Историческое предприятие",
        latitude=55.8031,
        longitude=37.6917,
        created_at=timestamp,
        updated_at=timestamp,
    )


@pytest.mark.asyncio
async def test_create_keeps_submission_out_of_places() -> None:
    submissions = AsyncMock()
    places = AsyncMock()
    pending = submission_record(SubmissionStatus.PENDING)
    submissions.create.return_value = pending
    service = PlaceSubmissionService(submissions, places)
    proposal = NewPlaceSubmission("Завод", None, 55.8, 37.6, ())

    created = await service.create(proposal)

    assert created is pending
    places.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_approve_creates_one_place_and_records_it() -> None:
    submissions = AsyncMock()
    places = AsyncMock()
    pending = submission_record(SubmissionStatus.PENDING)
    place_id = uuid4()
    approved = submission_record(
        SubmissionStatus.APPROVED,
        submission_id=pending.id,
        approved_place_id=place_id,
    )
    submissions.get_for_update.return_value = pending
    submissions.mark_approved.return_value = approved
    places.create.return_value = place_record(place_id)
    service = PlaceSubmissionService(submissions, places)

    result = await service.approve(pending.id, "Источники проверены")

    assert result is approved
    places.create.assert_awaited_once()
    new_place = places.create.await_args.args[0]
    assert new_place.longitude == 37.6917
    assert new_place.latitude == 55.8031
    submissions.mark_approved.assert_awaited_once_with(
        pending.id,
        place_id,
        "Источники проверены",
    )


@pytest.mark.asyncio
async def test_repeated_approval_does_not_create_duplicate_place() -> None:
    submissions = AsyncMock()
    places = AsyncMock()
    approved = submission_record(
        SubmissionStatus.APPROVED,
        approved_place_id=uuid4(),
    )
    submissions.get_for_update.return_value = approved

    result = await PlaceSubmissionService(submissions, places).approve(approved.id)

    assert result is approved
    places.create.assert_not_awaited()
    submissions.mark_approved.assert_not_awaited()


@pytest.mark.asyncio
async def test_reject_preserves_submission_without_creating_place() -> None:
    submissions = AsyncMock()
    places = AsyncMock()
    pending = submission_record(SubmissionStatus.PENDING)
    rejected = submission_record(
        SubmissionStatus.REJECTED,
        submission_id=pending.id,
    )
    submissions.get_for_update.return_value = pending
    submissions.mark_rejected.return_value = rejected

    result = await PlaceSubmissionService(submissions, places).reject(
        pending.id,
        "Недостаточно источников",
    )

    assert result is rejected
    places.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_final_decisions_cannot_be_reversed() -> None:
    submissions = AsyncMock()
    places = AsyncMock()
    service = PlaceSubmissionService(submissions, places)
    rejected = submission_record(SubmissionStatus.REJECTED)
    submissions.get_for_update.return_value = rejected

    with pytest.raises(InvalidSubmissionTransition):
        await service.approve(rejected.id)

    approved = submission_record(
        SubmissionStatus.APPROVED,
        approved_place_id=uuid4(),
    )
    submissions.get_for_update.return_value = approved
    with pytest.raises(InvalidSubmissionTransition):
        await service.reject(approved.id)


@pytest.mark.asyncio
async def test_missing_submission_raises_not_found() -> None:
    submissions = AsyncMock()
    places = AsyncMock()
    submissions.get_for_update.return_value = None

    with pytest.raises(SubmissionNotFound):
        await PlaceSubmissionService(submissions, places).approve(uuid4())
