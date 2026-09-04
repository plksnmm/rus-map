from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from rus_map.models import MaterialType
from rus_map.repositories.material import MaterialRepository


@pytest.mark.asyncio
async def test_list_returns_latest_published_materials() -> None:
    place_id = uuid4()
    material_id = uuid4()
    timestamp = datetime.now(UTC)
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = place_id
    rows = Mock()
    rows.all.return_value = [
        (
            material_id,
            MaterialType.EXTERNAL_LINK,
            "Репортаж",
            "Русь пролетарская",
            2,
            None,
            "https://example.com/report",
            None,
            timestamp,
            timestamp,
            timestamp,
        ),
    ]
    execute_result = Mock()
    execute_result.tuples.return_value = rows
    session.execute.return_value = execute_result

    page = await MaterialRepository(session).list_published_for_place(place_id)

    assert page is not None
    assert page.total == 1
    assert page.items[0].id == material_id
    assert page.items[0].revision_number == 2
    assert page.items[0].url == "https://example.com/report"

    statement = session.execute.await_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "row_number() OVER" in sql
    assert "app.materials.status" in sql
    assert "material_revisions.status" in sql
    assert "ORDER BY app.materials.created_at, app.materials.id" in sql


@pytest.mark.asyncio
async def test_list_returns_empty_page_for_existing_place() -> None:
    place_id = uuid4()
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = place_id
    rows = Mock()
    rows.all.return_value = []
    execute_result = Mock()
    execute_result.tuples.return_value = rows
    session.execute.return_value = execute_result

    page = await MaterialRepository(session).list_published_for_place(place_id)

    assert page is not None
    assert page.items == []
    assert page.total == 0


@pytest.mark.asyncio
async def test_list_returns_none_for_unknown_place() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None

    page = await MaterialRepository(session).list_published_for_place(uuid4())

    assert page is None
    session.execute.assert_not_awaited()
