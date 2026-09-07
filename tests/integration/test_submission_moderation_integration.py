import os

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rus_map.db.session import get_engine
from rus_map.models import Place, PlaceSubmission, SubmissionStatus
from rus_map.repositories.place import PlaceRepository
from rus_map.repositories.submission import (
    NewPlaceSubmission,
    PlaceSubmissionRepository,
)
from rus_map.services.submission import PlaceSubmissionService

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "1",
        reason="set RUN_INTEGRATION_TESTS=1 to run database tests",
    ),
]


@pytest.mark.asyncio
async def test_approval_creates_exactly_one_place_in_same_transaction() -> None:
    engine = get_engine()

    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            session = AsyncSession(bind=connection, expire_on_commit=False)

            try:
                service = PlaceSubmissionService(
                    PlaceSubmissionRepository(session),
                    PlaceRepository(session),
                )
                pending = await service.create(
                    NewPlaceSubmission(
                        title="Integration-test submission",
                        description="Temporary proposal",
                        latitude=55.8,
                        longitude=37.6,
                        source_urls=("https://example.com/source",),
                    )
                )
                assert pending.status is SubmissionStatus.PENDING
                assert (
                    await session.scalar(
                        select(func.count())
                        .select_from(Place)
                        .where(Place.title == "Integration-test submission")
                    )
                    == 0
                )

                first = await service.approve(pending.id, "Проверено")
                second = await service.approve(pending.id, "Повтор")

                assert first.status is SubmissionStatus.APPROVED
                assert second.approved_place_id == first.approved_place_id
                assert first.approved_place_id is not None
                assert (
                    await session.scalar(
                        select(func.count())
                        .select_from(Place)
                        .where(Place.id == first.approved_place_id)
                    )
                    == 1
                )
                stored = await session.get(PlaceSubmission, pending.id)
                assert stored is not None
                assert stored.review_notes == "Проверено"
            finally:
                await session.close()
                if transaction.is_active:
                    await transaction.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_rejection_keeps_audit_record_without_place() -> None:
    engine = get_engine()

    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            session = AsyncSession(bind=connection, expire_on_commit=False)

            try:
                service = PlaceSubmissionService(
                    PlaceSubmissionRepository(session),
                    PlaceRepository(session),
                )
                pending = await service.create(
                    NewPlaceSubmission(
                        title="Rejected integration-test submission",
                        description=None,
                        latitude=55.8,
                        longitude=37.6,
                        source_urls=(),
                    )
                )
                rejected = await service.reject(pending.id, "Нет источников")

                assert rejected.status is SubmissionStatus.REJECTED
                assert rejected.approved_place_id is None
                assert (
                    await session.scalar(
                        select(func.count())
                        .select_from(Place)
                        .where(Place.title == "Rejected integration-test submission")
                    )
                    == 0
                )
                assert (
                    await session.scalar(
                        select(func.count())
                        .select_from(PlaceSubmission)
                        .where(PlaceSubmission.id == pending.id)
                    )
                    == 1
                )
            finally:
                await session.close()
                if transaction.is_active:
                    await transaction.rollback()
    finally:
        await engine.dispose()
