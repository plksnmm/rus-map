import hashlib
import io
import os
from pathlib import Path
from uuid import uuid4

import pytest
from geoalchemy2.elements import WKTElement
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from rus_map.admin.image_import import (
    PlaceImagesManifest,
    import_place_images,
    prepare_image,
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
async def test_image_manifest_is_idempotent_in_postgresql(tmp_path: Path) -> None:
    output = io.BytesIO()
    Image.new("RGB", (40, 20), "black").save(output, format="JPEG")
    source = output.getvalue()
    (tmp_path / "factory.jpg").write_bytes(source)
    place_id = uuid4()
    manifest = PlaceImagesManifest.model_validate(
        {
            "schema_version": 1,
            "place_id": str(place_id),
            "images": [
                {
                    "media_id": str(uuid4()),
                    "material_id": str(uuid4()),
                    "revision_id": str(uuid4()),
                    "status": "published",
                    "title": "Архивная фотография завода",
                    "source": "Integration test",
                    "source_url": "https://example.com/archive",
                    "file": "factory.jpg",
                    "sha256": hashlib.sha256(source).hexdigest(),
                }
            ],
        }
    )
    prepared = [prepare_image(manifest.images[0], tmp_path)]
    engine = get_engine()

    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            session = AsyncSession(bind=connection, expire_on_commit=False)
            try:
                session.add(
                    Place(
                        id=place_id,
                        title="Завод для проверки изображений",
                        description=None,
                        location=WKTElement("POINT(37.8 55.7)", srid=4326),
                    )
                )
                await session.flush()
                first = await import_place_images(session, manifest, prepared)
                second = await import_place_images(session, manifest, prepared)

                assert (
                    first.created_assets,
                    first.created_materials,
                    first.created_revisions,
                ) == (1, 1, 1)
                assert (
                    second.existing_assets,
                    second.existing_materials,
                    second.existing_revisions,
                ) == (1, 1, 1)
            finally:
                await session.close()
                if transaction.is_active:
                    await transaction.rollback()
    finally:
        await engine.dispose()
