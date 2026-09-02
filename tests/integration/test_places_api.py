import os
from collections.abc import AsyncIterator

import pytest
from geoalchemy2.elements import WKTElement
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from rus_map.db.session import get_engine, get_session
from rus_map.main import create_app
from rus_map.models import Place

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "1",
        reason="set RUN_INTEGRATION_TESTS=1 to run database tests",
    ),
]


@pytest.mark.asyncio
async def test_list_places_reads_postgis_data() -> None:
    """The HTTP endpoint returns a place inserted into PostgreSQL."""
    engine = get_engine()
    application = create_app()

    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            session = AsyncSession(
                bind=connection,
                expire_on_commit=False,
            )

            try:
                place = Place(
                    title="Завод Красный богатырь",
                    description="Integration-test record",
                    location=WKTElement(
                        "POINT(37.6917 55.8031)",
                        srid=4326,
                    ),
                )
                session.add(place)
                await session.flush()

                async def override_get_session() -> AsyncIterator[AsyncSession]:
                    yield session

                application.dependency_overrides[get_session] = override_get_session

                async with AsyncClient(
                    transport=ASGITransport(app=application),
                    base_url="http://test",
                ) as client:
                    response = await client.get("/api/v1/places")

                assert response.status_code == 200
                body = response.json()
                returned_place = next(
                    item for item in body["items"] if item["id"] == str(place.id)
                )
                assert returned_place == {
                    "id": str(place.id),
                    "title": "Завод Красный богатырь",
                    "latitude": 55.8031,
                    "longitude": 37.6917,
                }
                assert body["total"] >= 1
            finally:
                application.dependency_overrides.clear()
                await session.close()
                if transaction.is_active:
                    await transaction.rollback()
    finally:
        await engine.dispose()
