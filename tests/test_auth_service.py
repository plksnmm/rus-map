from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import SecretStr

from rus_map.config import Settings
from rus_map.repositories.auth import AdminRecord, AuthenticatedSession
from rus_map.services.auth import (
    AdminAuthService,
    InvalidCredentialsError,
    LoginRateLimitedError,
    hash_password,
    hash_token,
    password_hasher,
)


def settings() -> Settings:
    return Settings(
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="rus_map",
        postgres_user="rus_map",
        postgres_password=SecretStr("secret"),
    )


@pytest.mark.asyncio
async def test_login_creates_hashed_opaque_session() -> None:
    repository = AsyncMock()
    admin = AdminRecord(uuid4(), "editor", hash_password("correct horse battery"), True)
    repository.get_admin_by_username.return_value = admin
    repository.any_throttle_blocked.return_value = False
    repository.create_session.return_value = uuid4()

    result = await AdminAuthService(repository, settings()).login(
        " Editor ", "correct horse battery", "127.0.0.1"
    )

    assert result.session.username == "editor"
    assert len(result.session_token) >= 32
    assert len(result.csrf_token) >= 32
    stored = repository.create_session.await_args.args
    assert stored[0] == admin.id
    assert stored[1] == hash_token(result.session_token)
    assert stored[1] != result.session_token
    assert stored[2] == hash_token(result.csrf_token)
    repository.clear_throttles.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("known_user", [True, False])
async def test_bad_username_and_password_raise_same_error(known_user: bool) -> None:
    repository = AsyncMock()
    repository.any_throttle_blocked.return_value = False
    repository.get_admin_by_username.return_value = (
        AdminRecord(uuid4(), "editor", hash_password("correct password"), True)
        if known_user
        else None
    )
    service = AdminAuthService(repository, settings())

    with pytest.raises(InvalidCredentialsError):
        await service.login("editor", "wrong password", "192.0.2.1")

    repository.record_failed_attempt.assert_awaited_once()
    repository.commit_failed_attempt.assert_awaited_once_with()
    repository.create_session.assert_not_awaited()


@pytest.mark.asyncio
async def test_blocked_login_skips_password_lookup() -> None:
    repository = AsyncMock()
    repository.any_throttle_blocked.return_value = True

    with pytest.raises(LoginRateLimitedError):
        await AdminAuthService(repository, settings()).login(
            "editor", "anything", "192.0.2.1"
        )

    repository.get_admin_by_username.assert_not_awaited()


@pytest.mark.asyncio
async def test_authenticate_revokes_and_validates_csrf() -> None:
    repository = AsyncMock()
    csrf = "csrf-token"
    active = AuthenticatedSession(
        session_id=uuid4(),
        admin_id=uuid4(),
        username="editor",
        csrf_token_hash=hash_token(csrf),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    repository.get_active_session.return_value = active
    service = AdminAuthService(repository, settings())

    assert await service.authenticate("session-token") is active
    service.verify_csrf(active, csrf)
    with pytest.raises(InvalidCredentialsError):
        service.verify_csrf(active, "wrong")

    await service.logout(active)
    repository.revoke_session.assert_awaited_once()


def test_password_hash_uses_argon2id() -> None:
    encoded = hash_password("a sufficiently long password")
    assert encoded.startswith("$argon2id$")
    assert password_hasher.verify("a sufficiently long password", encoded)
