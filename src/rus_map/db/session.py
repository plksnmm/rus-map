from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from rus_map.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    """Create and cache the application's asynchronous database engine."""
    settings = get_settings()

    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
    )


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create and cache the asynchronous session factory."""
    return async_sessionmaker(
        bind=get_engine(),
        expire_on_commit=False,
    )


async def get_session() -> AsyncIterator[AsyncSession]:
    """Provide one database session and close it after use."""
    async with get_session_factory()() as session:
        yield session
