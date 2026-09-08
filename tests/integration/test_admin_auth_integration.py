import os
from collections.abc import AsyncIterator

import pytest
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rus_map.config import get_settings
from rus_map.db.session import get_engine, get_session
from rus_map.main import create_app
from rus_map.models import AdminLoginThrottle, AdminSession
from rus_map.repositories.auth import AdminAuthRepository
from rus_map.services.auth import hash_password, throttle_keys

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "1",
        reason="set RUN_INTEGRATION_TESTS=1 to run database tests",
    ),
]


@pytest.mark.asyncio
async def test_login_current_admin_and_csrf_protected_logout() -> None:
    engine = get_engine()
    application = create_app()

    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            session = AsyncSession(bind=connection, expire_on_commit=False)

            try:
                admin = await AdminAuthRepository(session).create_admin(
                    "integration-admin",
                    hash_password("integration password 123"),
                )

                async def override_get_session() -> AsyncIterator[AsyncSession]:
                    yield session

                application.dependency_overrides[get_session] = override_get_session
                async with AsyncClient(
                    transport=ASGITransport(app=application),
                    base_url="http://test",
                ) as client:
                    login = await client.post(
                        "/api/v1/admin/auth/login",
                        json={
                            "username": "INTEGRATION-ADMIN",
                            "password": "integration password 123",
                        },
                    )
                    assert login.status_code == 200
                    assert login.json()["admin"]["id"] == str(admin.id)
                    assert "integration password 123" not in login.text

                    session_cookie = get_settings().admin_session_cookie_name
                    raw_session_token = client.cookies.get(session_cookie)
                    assert raw_session_token
                    current = await client.get("/api/v1/admin/auth/me")
                    assert current.status_code == 200
                    assert current.json()["username"] == "integration-admin"

                    without_csrf = await client.post("/api/v1/admin/auth/logout")
                    assert without_csrf.status_code == 403

                    csrf_token = client.cookies.get(
                        get_settings().admin_csrf_cookie_name
                    )
                    logout = await client.post(
                        "/api/v1/admin/auth/logout",
                        headers={"X-CSRF-Token": csrf_token or ""},
                    )
                    assert logout.status_code == 204

                stored_session = (
                    await session.execute(
                        select(AdminSession).where(AdminSession.admin_id == admin.id)
                    )
                ).scalar_one()
                assert stored_session.token_hash != raw_session_token
                assert stored_session.revoked_at is not None
            finally:
                application.dependency_overrides.clear()
                await session.close()
                if transaction.is_active:
                    await transaction.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_failed_login_throttle_survives_error_and_clears_on_success() -> None:
    engine = get_engine()
    application = create_app()

    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            session = AsyncSession(bind=connection, expire_on_commit=False)

            try:
                await AdminAuthRepository(session).create_admin(
                    "throttle-integration-admin",
                    hash_password("integration password 123"),
                )

                async def override_get_session() -> AsyncIterator[AsyncSession]:
                    yield session

                application.dependency_overrides[get_session] = override_get_session
                username_throttle = throttle_keys(
                    "throttle-integration-admin", "unused"
                )[0]
                async with AsyncClient(
                    transport=ASGITransport(app=application),
                    base_url="http://test",
                ) as client:
                    failed = await client.post(
                        "/api/v1/admin/auth/login",
                        json={
                            "username": "throttle-integration-admin",
                            "password": "wrong password",
                        },
                    )
                    assert failed.status_code == 401
                    assert (
                        await session.scalar(
                            select(AdminLoginThrottle.failed_attempts).where(
                                AdminLoginThrottle.key_hash == username_throttle
                            )
                        )
                        == 1
                    )

                    success = await client.post(
                        "/api/v1/admin/auth/login",
                        json={
                            "username": "throttle-integration-admin",
                            "password": "integration password 123",
                        },
                    )
                    assert success.status_code == 200
                    assert (
                        await session.scalar(
                            select(AdminLoginThrottle.failed_attempts).where(
                                AdminLoginThrottle.key_hash == username_throttle
                            )
                        )
                        is None
                    )
            finally:
                application.dependency_overrides.clear()
                await session.close()
                if transaction.is_active:
                    await transaction.rollback()
    finally:
        await engine.dispose()
