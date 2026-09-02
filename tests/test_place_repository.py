from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from rus_map.repositories.place import NewPlace, PlaceRepository


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


@pytest.mark.asyncio
async def test_create_inserts_longitude_before_latitude() -> None:
    place_id = uuid4()
    timestamp = datetime.now(UTC)
    session = AsyncMock(spec=AsyncSession)
    result = Mock()
    result.one.return_value = (
        place_id,
        "Завод Красный богатырь",
        "Историческое здание",
        55.8031,
        37.6917,
        timestamp,
        timestamp,
    )
    execute_result = Mock()
    execute_result.tuples.return_value = result
    session.execute.return_value = execute_result

    created = await PlaceRepository(session).create(
        NewPlace(
            title="Завод Красный богатырь",
            description="Историческое здание",
            latitude=55.8031,
            longitude=37.6917,
        ),
    )

    assert created.id == place_id
    assert created.latitude == 55.8031
    assert created.longitude == 37.6917
    assert created.created_at == timestamp
    assert created.updated_at == timestamp

    statement = session.execute.await_args.args[0]
    sql = str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        ),
    )
    assert "ST_MakePoint(37.6917, 55.8031)" in sql
    assert "ST_SetSRID" in sql
    assert "RETURNING" in sql
