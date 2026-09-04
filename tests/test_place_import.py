from typing import cast
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import UUID

import pytest
from geoalchemy2.elements import WKTElement
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rus_map.admin.place_import import (
    ManifestConflictError,
    PlacesManifest,
    execute_import,
    import_places,
)

PLACE_ID = UUID("11111111-1111-4111-8111-111111111111")


def manifest() -> PlacesManifest:
    return PlacesManifest.model_validate(
        {
            "schema_version": 1,
            "places": [
                {
                    "id": str(PLACE_ID),
                    "title": "Кусковский химический завод",
                    "description": "Проверенная историческая справка.",
                    "latitude": 55.74,
                    "longitude": 37.75,
                },
            ],
        },
    )


def execute_result_with(row: tuple[object, ...] | None) -> Mock:
    tuples = Mock()
    tuples.one_or_none.return_value = row
    result = Mock()
    result.tuples.return_value = tuples
    return result


@pytest.mark.asyncio
async def test_import_stages_place_with_longitude_before_latitude() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = execute_result_with(None)

    result = await import_places(session, manifest())

    assert result.created_places == 1
    assert result.existing_places == 0
    added = session.add.call_args.args[0]
    assert added.id == PLACE_ID
    assert isinstance(added.location, WKTElement)
    assert added.location.data == "POINT(37.75 55.74)"
    assert added.location.srid == 4326
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_repeated_identical_import_is_a_no_op() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = execute_result_with(
        (
            PLACE_ID,
            "Кусковский химический завод",
            "Проверенная историческая справка.",
            55.74000001,
            37.74999999,
        ),
    )

    result = await import_places(session, manifest())

    assert result.created_places == 0
    assert result.existing_places == 1
    session.add.assert_not_called()
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_import_rejects_stable_id_conflict() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = execute_result_with(
        (
            PLACE_ID,
            "Другое место",
            "Проверенная историческая справка.",
            55.74,
            37.75,
        ),
    )

    with pytest.raises(ManifestConflictError, match=str(PLACE_ID)):
        await import_places(session, manifest())

    session.add.assert_not_called()
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
    session.execute.return_value = execute_result_with(None)

    result = await execute_import(
        manifest(),
        dry_run=True,
        session_factory=session_factory_for(session),
    )

    assert result.created_places == 1
    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_successful_import_commits() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = execute_result_with(None)

    await execute_import(
        manifest(),
        dry_run=False,
        session_factory=session_factory_for(session),
    )

    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_failed_import_rolls_back_everything() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = execute_result_with(
        (PLACE_ID, "Другое место", None, 55.74, 37.75),
    )

    with pytest.raises(ManifestConflictError):
        await execute_import(
            manifest(),
            dry_run=False,
            session_factory=session_factory_for(session),
        )

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
