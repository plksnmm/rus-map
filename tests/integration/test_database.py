import os

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from rus_map.db.check import check_database_connection
from rus_map.db.session import get_engine

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "1",
        reason="set RUN_INTEGRATION_TESTS=1 to run database tests",
    ),
]


@pytest.mark.asyncio
async def test_database_connection_and_postgis_extension() -> None:
    try:
        database, postgis_version = await check_database_connection()

        assert database == "rus_map"
        assert postgis_version.startswith("3.6")
    finally:
        await get_engine().dispose()


@pytest.mark.asyncio
async def test_database_has_current_places_schema() -> None:
    """The migrated database has the expected revision and spatial objects."""
    engine = get_engine()
    expected_revision = ScriptDirectory.from_config(
        Config("alembic.ini", toml_file="pyproject.toml"),
    ).get_current_head()

    try:
        async with engine.connect() as connection:
            current_revision = await connection.scalar(
                text("SELECT version_num FROM alembic_version"),
            )
            geometry = (
                await connection.execute(
                    text(
                        """
                        SELECT type, srid
                        FROM geometry_columns
                        WHERE f_table_schema = 'app'
                          AND f_table_name = 'places'
                          AND f_geometry_column = 'location'
                        """,
                    ),
                )
            ).one()
            index_definition = await connection.scalar(
                text(
                    """
                    SELECT indexdef
                    FROM pg_indexes
                    WHERE schemaname = 'app'
                      AND tablename = 'places'
                      AND indexname = 'idx_places_location'
                    """,
                ),
            )

        assert current_revision == expected_revision
        assert geometry._tuple() == ("POINT", 4326)
        assert index_definition is not None
        assert "USING gist" in index_definition
    finally:
        await engine.dispose()
