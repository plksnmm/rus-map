import os

import pytest

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
