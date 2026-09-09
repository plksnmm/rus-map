import os
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from rus_map.config import get_settings
from rus_map.db.session import get_engine, get_session
from rus_map.main import create_app
from rus_map.models import SubmissionStatus
from rus_map.repositories.auth import AdminAuthRepository
from rus_map.repositories.submission import (
    NewPlaceSubmission,
    PlaceSubmissionRepository,
)
from rus_map.services.auth import hash_password

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "1",
        reason="set RUN_INTEGRATION_TESTS=1 to run database tests",
    ),
]


@pytest.mark.asyncio
async def test_authenticated_admin_lists_and_approves_submission() -> None:
    engine = get_engine()
    application = create_app()

    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            session = AsyncSession(bind=connection, expire_on_commit=False)

            try:
                suffix = uuid4().hex
                admin = await AdminAuthRepository(session).create_admin(
                    f"moderator-{suffix}",
                    hash_password("integration password 123"),
                )
                pending = await PlaceSubmissionRepository(session).create(
                    NewPlaceSubmission(
                        title=f"Integration moderation {suffix}",
                        description="Temporary proposal",
                        latitude=55.8,
                        longitude=37.6,
                        source_urls=("https://example.com/source",),
                    )
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
                            "username": admin.username,
                            "password": "integration password 123",
                        },
                    )
                    assert login.status_code == 200

                    queue = await client.get("/api/v1/admin/submissions?status=pending")
                    assert queue.status_code == 200
                    assert str(pending.id) in {
                        item["id"] for item in queue.json()["items"]
                    }

                    csrf_token = client.cookies.get(
                        get_settings().admin_csrf_cookie_name
                    )
                    without_csrf = await client.post(
                        f"/api/v1/admin/submissions/{pending.id}/approve",
                        json={"review_notes": "Проверено"},
                    )
                    approved = await client.post(
                        f"/api/v1/admin/submissions/{pending.id}/approve",
                        headers={"X-CSRF-Token": csrf_token or ""},
                        json={"review_notes": "Проверено"},
                    )

                assert without_csrf.status_code == 403
                assert approved.status_code == 200
                body = approved.json()
                assert body["status"] == SubmissionStatus.APPROVED
                assert body["moderated_by_admin_id"] == str(admin.id)
                assert body["approved_place_id"] is not None
            finally:
                application.dependency_overrides.clear()
                await session.close()
                if transaction.is_active:
                    await transaction.rollback()
    finally:
        await engine.dispose()
