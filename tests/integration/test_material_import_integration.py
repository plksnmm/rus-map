import os
from uuid import uuid4

import pytest
from geoalchemy2.elements import WKTElement
from sqlalchemy.ext.asyncio import AsyncSession

from rus_map.admin.material_import import (
    PlaceMaterialsManifest,
    import_place_materials,
)
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
async def test_material_manifest_is_idempotent_in_postgresql() -> None:
    """A second import sees the same stable records and creates nothing."""
    engine = get_engine()

    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            session = AsyncSession(bind=connection, expire_on_commit=False)
            place_id = uuid4()
            material_id = uuid4()
            revision_id = uuid4()

            try:
                session.add(
                    Place(
                        id=place_id,
                        title="Тестовый завод для импорта",
                        description=None,
                        location=WKTElement("POINT(60.8 56.5)", srid=4326),
                    ),
                )
                await session.flush()
                manifest = PlaceMaterialsManifest.model_validate(
                    {
                        "schema_version": 1,
                        "place_id": str(place_id),
                        "materials": [
                            {
                                "id": str(material_id),
                                "type": "text",
                                "status": "published",
                                "title": "История предприятия",
                                "source": "Integration test",
                                "revisions": [
                                    {
                                        "id": str(revision_id),
                                        "revision_number": 1,
                                        "status": "published",
                                        "content": "Проверенная редакция.",
                                    },
                                ],
                            },
                        ],
                    },
                )

                first = await import_place_materials(session, manifest)
                second = await import_place_materials(session, manifest)

                assert first.created_materials == 1
                assert first.created_revisions == 1
                assert second.existing_materials == 1
                assert second.existing_revisions == 1
                assert second.created_materials == 0
                assert second.created_revisions == 0
            finally:
                await session.close()
                if transaction.is_active:
                    await transaction.rollback()
    finally:
        await engine.dispose()
