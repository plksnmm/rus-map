from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from rus_map.repositories.place import PlaceRepository


@pytest.mark.asyncio
async def test_list_returns_places_and_total() -> None:
    place_id = uuid4()
    session = AsyncMock(spec=AsyncSession)
    result = Mock()
    result.all.return_value = [
        (place_id, "Завод Красный богатырь", 55.8031, 37.6917, 1),
    ]
    execute_result = Mock()
    execute_result.tuples.return_value = result
    session.execute.return_value = execute_result

    page = await PlaceRepository(session).list()

    assert page.total == 1
    assert len(page.items) == 1
    assert page.items[0].id == place_id
    assert page.items[0].title == "Завод Красный богатырь"
    assert page.items[0].latitude == 55.8031
    assert page.items[0].longitude == 37.6917

    statement = session.execute.await_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "ST_Y" in sql
    assert "ST_X" in sql
    assert "count(*) OVER" in sql
    assert "ORDER BY app.places.created_at, app.places.id" in sql


@pytest.mark.asyncio
async def test_list_returns_empty_page() -> None:
    session = AsyncMock(spec=AsyncSession)
    result = Mock()
    result.all.return_value = []
    execute_result = Mock()
    execute_result.tuples.return_value = result
    session.execute.return_value = execute_result

    page = await PlaceRepository(session).list()

    assert page.items == []
    assert page.total == 0
