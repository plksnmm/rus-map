import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from rus_map.config import get_settings
from rus_map.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = get_settings().database_url
target_metadata = Base.metadata
APPLICATION_SCHEMA = "app"


def include_name(
    name: str | None,
    type_: str,
    parent_names: dict[str, str | None],
) -> bool:
    """Restrict autogenerate to objects owned by the application schema."""
    del parent_names

    if type_ == "schema":
        return name == APPLICATION_SCHEMA

    return True


def run_migrations_offline() -> None:
    """Generate SQL without connecting to the database."""
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_schemas=True,
        include_name=include_name,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations using an established database connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        include_schemas=True,
        include_name=include_name,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create a temporary async engine and run migrations."""
    connectable = create_async_engine(
        database_url,
        poolclass=pool.NullPool,
    )

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations against the configured database."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
