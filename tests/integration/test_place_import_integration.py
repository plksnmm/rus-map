import os
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rus_map.admin.place_import import PlacesManifest, import_places
from rus_map.db.session import get_engine
from rus_map.models import Place

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "1",
        reason="set RUN_INTEGRATION_TESTS=1 to run database tests",
    ),
]


@pytest.mark.asyncio
async def test_place_manifest_is_idempotent_and_uses_postgis_point() -> None:
    """A second import creates nothing and coordinates survive round-trip."""
    engine = get_engine()
    place_id = uuid4()

    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            session = AsyncSession(bind=connection, expire_on_commit=False)

            try:
                manifest = PlacesManifest.model_validate(
                    {
                        "schema_version": 1,
                        "places": [
                            {
                                "id": str(place_id),
                                "title": "Integration-test factory",
                                "description": "Temporary record",
                                "latitude": 55.74,
                                "longitude": 37.75,
                            },
                        ],
                    },
                )

                first = await import_places(session, manifest)
                second = await import_places(session, manifest)
                stored = (
                    await session.execute(
                        select(
                            func.ST_GeometryType(Place.location),
                            func.ST_SRID(Place.location),
                            func.ST_Y(Place.location),
                            func.ST_X(Place.location),
                        ).where(Place.id == place_id),
                    )
                ).one()

                assert first.created_places == 1
                assert second.existing_places == 1
                assert second.created_places == 0
                assert stored == ("ST_Point", 4326, 55.74, 37.75)
            finally:
                await session.close()
                if transaction.is_active:
                    await transaction.rollback()
    finally:
        await engine.dispose()
