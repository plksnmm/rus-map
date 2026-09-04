from typing import cast
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rus_map.admin.material_import import (
    ManifestConflictError,
    PlaceMaterialsManifest,
    PlaceNotFoundError,
    execute_import,
    import_place_materials,
)
from rus_map.models import Material, MaterialRevision, MaterialType, Place

PLACE_ID = UUID("11111111-1111-4111-8111-111111111111")
MATERIAL_ID = UUID("22222222-2222-4222-8222-222222222222")
REVISION_ID = UUID("33333333-3333-4333-8333-333333333333")


def manifest() -> PlaceMaterialsManifest:
    return PlaceMaterialsManifest.model_validate(
        {
            "schema_version": 1,
            "place_id": str(PLACE_ID),
            "materials": [
                {
                    "id": str(MATERIAL_ID),
                    "type": "external_link",
                    "title": "Архивный источник",
                    "source": "Русь пролетарская",
                    "revisions": [
                        {
                            "id": str(REVISION_ID),
                            "revision_number": 1,
                            "url": "https://example.com/archive",
                        },
                    ],
                },
            ],
        },
    )


@pytest.mark.asyncio
async def test_import_stages_new_material_and_revision() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.get.side_effect = [Place(id=PLACE_ID), None, None]
    session.scalar.return_value = None

    result = await import_place_materials(session, manifest())

    assert result.created_materials == 1
    assert result.created_revisions == 1
    assert result.existing_materials == 0
    assert result.existing_revisions == 0
    added = [call.args[0] for call in session.add.call_args_list]
    assert isinstance(added[0], Material)
    assert added[0].id == MATERIAL_ID
    assert added[0].type is MaterialType.EXTERNAL_LINK
    assert isinstance(added[1], MaterialRevision)
    assert added[1].id == REVISION_ID
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_repeated_identical_import_is_a_no_op() -> None:
    expected = manifest().materials[0]
    existing_material = Material(
        id=expected.id,
        place_id=PLACE_ID,
        type=expected.type,
        status=expected.status,
        title=expected.title,
        source=expected.source,
    )
    revision = expected.revisions[0]
    existing_revision = MaterialRevision(
        id=revision.id,
        material_id=expected.id,
        revision_number=revision.revision_number,
        status=revision.status,
        content=revision.content,
        url=revision.url,
    )
    session = AsyncMock(spec=AsyncSession)
    session.get.side_effect = [Place(id=PLACE_ID), existing_material, existing_revision]

    result = await import_place_materials(session, manifest())

    assert result.created_materials == 0
    assert result.created_revisions == 0
    assert result.existing_materials == 1
    assert result.existing_revisions == 1
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_import_rejects_unknown_place() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.get.return_value = None

    with pytest.raises(PlaceNotFoundError, match=str(PLACE_ID)):
        await import_place_materials(session, manifest())

    session.add.assert_not_called()
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_import_rejects_stable_id_conflict() -> None:
    conflicting_material = Material(
        id=MATERIAL_ID,
        place_id=PLACE_ID,
        type=MaterialType.VIDEO,
        title="Другой материал",
        source=None,
    )
    session = AsyncMock(spec=AsyncSession)
    session.get.side_effect = [Place(id=PLACE_ID), conflicting_material]

    with pytest.raises(ManifestConflictError, match=str(MATERIAL_ID)):
        await import_place_materials(session, manifest())

    session.add.assert_not_called()
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_import_rejects_existing_revision_number_with_another_id() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.get.side_effect = [Place(id=PLACE_ID), None, None]
    other_revision_id = UUID("44444444-4444-4444-8444-444444444444")
    session.scalar.return_value = other_revision_id

    with pytest.raises(ManifestConflictError, match=str(other_revision_id)):
        await import_place_materials(session, manifest())

    session.flush.assert_not_awaited()


def session_factory_for(
    session: AsyncMock,
) -> async_sessionmaker[AsyncSession]:
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=context)
    return cast(async_sessionmaker[AsyncSession], factory)


@pytest.mark.asyncio
async def test_dry_run_always_rolls_back() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.get.side_effect = [Place(id=PLACE_ID), None, None]
    session.scalar.return_value = None

    result = await execute_import(
        manifest(),
        dry_run=True,
        session_factory=session_factory_for(session),
    )

    assert result.created_materials == 1
    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_successful_import_commits() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.get.side_effect = [Place(id=PLACE_ID), None, None]
    session.scalar.return_value = None

    await execute_import(
        manifest(),
        dry_run=False,
        session_factory=session_factory_for(session),
    )

    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_failed_import_rolls_back_the_transaction() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.get.side_effect = [Place(id=PLACE_ID), None, None]
    session.scalar.return_value = UUID("44444444-4444-4444-8444-444444444444")

    with pytest.raises(ManifestConflictError):
        await execute_import(
            manifest(),
            dry_run=False,
            session_factory=session_factory_for(session),
        )

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
