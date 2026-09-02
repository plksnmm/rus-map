from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from rus_map.db.session import get_session


def make_session_factory_mock() -> tuple[Mock, AsyncMock]:
    """Return a session factory mock and the session yielded by its context."""
    session = AsyncMock(spec=AsyncSession)
    session_context = MagicMock()
    session_context.__aenter__ = AsyncMock(return_value=session)
    session_context.__aexit__ = AsyncMock(return_value=False)
    session_factory = Mock(return_value=session_context)

    return session_factory, session


@pytest.mark.asyncio
async def test_get_session_commits_successful_request() -> None:
    session_factory, session = make_session_factory_mock()

    with patch(
        "rus_map.db.session.get_session_factory",
        return_value=session_factory,
    ):
        dependency = get_session()

        assert await anext(dependency) is session
        with pytest.raises(StopAsyncIteration):
            await anext(dependency)

    session.commit.assert_awaited_once_with()
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_session_rolls_back_failed_request() -> None:
    session_factory, session = make_session_factory_mock()

    with patch(
        "rus_map.db.session.get_session_factory",
        return_value=session_factory,
    ):
        dependency = get_session()
        await anext(dependency)

        with pytest.raises(RuntimeError, match="request failed"):
            await dependency.athrow(RuntimeError("request failed"))

    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once_with()
