import os
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rus_map.api.routes import submissions
from rus_map.db.session import get_engine, get_session
from rus_map.main import create_app
from rus_map.models import Place, PlaceSubmission, SubmissionStatus

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "1",
        reason="set RUN_INTEGRATION_TESTS=1 to run database tests",
    ),
]


@pytest.mark.asyncio
async def test_public_proposal_is_pending_and_does_not_publish_place() -> None:
    engine = get_engine()
    application = create_app()

    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            session = AsyncSession(bind=connection, expire_on_commit=False)

            try:
                suffix = uuid4().hex
                title = f"Integration public submission {suffix}"

                async def override_get_session() -> AsyncIterator[AsyncSession]:
                    yield session

                application.dependency_overrides[get_session] = override_get_session
                submissions._requests.clear()
                async with AsyncClient(
                    transport=ASGITransport(app=application),
                    base_url="http://test",
                ) as client:
                    response = await client.post(
                        "/api/v1/submissions",
                        json={
                            "title": title,
                            "description": "Temporary proposal",
                            "latitude": 56.494711,
                            "longitude": 60.809612,
                            "address": "Сысерть, улица Тимирязева, 1",
                            "source_urls": ["https://example.com/source"],
                        },
                    )

                assert response.status_code == 202
                submission_id = UUID(response.json()["id"])
                stored = await session.get(PlaceSubmission, submission_id)
                assert stored is not None
                assert stored.status is SubmissionStatus.PENDING
                assert stored.address == "Сысерть, улица Тимирязева, 1"
                assert stored.source_urls == ["https://example.com/source"]
                assert (
                    await session.scalar(
                        select(func.count())
                        .select_from(Place)
                        .where(Place.title == title)
                    )
                    == 0
                )
            finally:
                submissions._requests.clear()
                application.dependency_overrides.clear()
                await session.close()
                if transaction.is_active:
                    await transaction.rollback()
    finally:
        await engine.dispose()
