from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from rus_map.api import dependencies as api_dependencies
from rus_map.api.dependencies import (
    get_admin_auth_service,
    get_current_admin_session,
    get_place_submission_service,
)
from rus_map.config import Settings
from rus_map.db import session as db_session
from rus_map.main import create_app
from rus_map.models import SubmissionStatus
from rus_map.repositories.auth import AuthenticatedSession
from rus_map.repositories.submission import PlaceSubmissionRecord
from rus_map.services.auth import InvalidCredentialsError
from rus_map.services.submission import InvalidSubmissionTransition, SubmissionNotFound


@pytest.fixture(autouse=True)
def auth_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    settings = Settings(
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="rus_map",
        postgres_user="rus_map",
        postgres_password=SecretStr("secret"),
        admin_cookie_secure=True,
        admin_cookie_path="/rus-map",
    )
    monkeypatch.setattr(api_dependencies, "get_settings", lambda: settings)
    return settings


def active_session() -> AuthenticatedSession:
    return AuthenticatedSession(
        session_id=uuid4(),
        admin_id=uuid4(),
        username="editor",
        csrf_token_hash="hash",
        expires_at=datetime.now(UTC) + timedelta(hours=12),
    )


def submission_record(
    status: SubmissionStatus = SubmissionStatus.PENDING,
    *,
    submission_id: UUID | None = None,
    admin_id: UUID | None = None,
) -> PlaceSubmissionRecord:
    timestamp = datetime.now(UTC)
    return PlaceSubmissionRecord(
        id=submission_id or uuid4(),
        status=status,
        title="Завод Красный богатырь",
        description="Историческое предприятие",
        latitude=55.8031,
        longitude=37.6917,
        source_urls=("https://example.com/factory",),
        review_notes=None,
        approved_place_id=uuid4() if status is SubmissionStatus.APPROVED else None,
        moderated_by_admin_id=(
            admin_id if status is not SubmissionStatus.PENDING else None
        ),
        moderated_at=None if status is SubmissionStatus.PENDING else timestamp,
        created_at=timestamp,
        updated_at=timestamp,
    )


def authenticated_application(
    service: MagicMock,
) -> tuple[object, AuthenticatedSession]:
    application = create_app()
    session = active_session()
    application.dependency_overrides[get_current_admin_session] = lambda: session
    application.dependency_overrides[get_place_submission_service] = lambda: service
    return application, session


def test_list_requires_authentication(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_if_database_settings_are_loaded() -> None:
        raise AssertionError("database dependency resolved before authentication")

    monkeypatch.setattr(
        db_session, "get_settings", fail_if_database_settings_are_loaded
    )
    application = create_app()
    auth_service = MagicMock()
    auth_service.authenticate = AsyncMock(side_effect=InvalidCredentialsError)
    application.dependency_overrides[get_admin_auth_service] = lambda: auth_service

    with TestClient(application) as client:
        response = client.get("/api/v1/admin/submissions")

    assert response.status_code == 401


def test_list_returns_filtered_paginated_queue() -> None:
    service = MagicMock()
    pending = submission_record()
    service.list = AsyncMock(return_value=([pending], 1))
    application, _session = authenticated_application(service)

    with TestClient(application) as client:
        response = client.get(
            "/api/v1/admin/submissions?status=pending&limit=20&offset=0"
        )

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == str(pending.id)
    assert response.json()["total"] == 1
    assert response.headers["cache-control"] == "no-store"
    service.list.assert_awaited_once_with(
        SubmissionStatus.PENDING,
        limit=20,
        offset=0,
    )


def test_detail_returns_not_found() -> None:
    service = MagicMock()
    service.get = AsyncMock(side_effect=SubmissionNotFound)
    application, _session = authenticated_application(service)

    with TestClient(application) as client:
        response = client.get(f"/api/v1/admin/submissions/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Submission not found"}


def test_approve_requires_csrf_and_records_current_admin() -> None:
    service = MagicMock()
    auth_service = MagicMock()
    auth_service.verify_csrf.side_effect = InvalidCredentialsError
    application, session = authenticated_application(service)
    application.dependency_overrides[get_admin_auth_service] = lambda: auth_service
    submission_id = uuid4()
    approved = submission_record(
        SubmissionStatus.APPROVED,
        submission_id=submission_id,
        admin_id=session.admin_id,
    )
    service.approve = AsyncMock(return_value=approved)

    with TestClient(application) as client:
        rejected = client.post(
            f"/api/v1/admin/submissions/{submission_id}/approve",
            json={"review_notes": "Источники проверены"},
        )
        auth_service.verify_csrf.side_effect = None
        accepted = client.post(
            f"/api/v1/admin/submissions/{submission_id}/approve",
            headers={"X-CSRF-Token": "csrf-secret"},
            json={"review_notes": "Источники проверены"},
        )

    assert rejected.status_code == 403
    assert accepted.status_code == 200
    assert accepted.json()["moderated_by_admin_id"] == str(session.admin_id)
    service.approve.assert_awaited_once_with(
        submission_id,
        session.admin_id,
        "Источники проверены",
    )


def test_reject_reports_final_transition_conflict() -> None:
    service = MagicMock()
    auth_service = MagicMock()
    service.reject = AsyncMock(side_effect=InvalidSubmissionTransition("approved"))
    application, _session = authenticated_application(service)
    application.dependency_overrides[get_admin_auth_service] = lambda: auth_service

    with TestClient(application) as client:
        response = client.post(
            f"/api/v1/admin/submissions/{uuid4()}/reject",
            headers={"X-CSRF-Token": "csrf-secret"},
            json={},
        )

    assert response.status_code == 409
    assert response.json() == {"detail": "approved"}
