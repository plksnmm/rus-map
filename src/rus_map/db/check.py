import asyncio

from sqlalchemy import text

from rus_map.db.session import get_engine


async def check_database_connection() -> tuple[str, str]:
    """Return the current database name and PostGIS version."""
    engine = get_engine()

    async with engine.connect() as connection:
        result = await connection.execute(
            text("SELECT current_database(), PostGIS_Version()"),
        )
        row = result.one()

    return str(row[0]), str(row[1])


async def main() -> None:
    """Run the database check from the command line."""
    engine = get_engine()

    try:
        database, postgis_version = await check_database_connection()
        print(f"Database: {database}")
        print(f"PostGIS: {postgis_version}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
