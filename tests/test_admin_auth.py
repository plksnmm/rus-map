from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import SecretStr

from rus_map.api.dependencies import get_admin_auth_service, get_current_admin_session
from rus_map.api.routes import admin_auth as admin_auth_routes
from rus_map.config import Settings
from rus_map.main import create_app
from rus_map.repositories.auth import AuthenticatedSession
from rus_map.services.auth import InvalidCredentialsError, LoginResult


def active_session() -> AuthenticatedSession:
    return AuthenticatedSession(
        session_id=uuid4(),
        admin_id=uuid4(),
        username="editor",
        csrf_token_hash="hash",
        expires_at=datetime.now(UTC) + timedelta(hours=12),
    )


def test_login_sets_hardened_session_and_csrf_cookies(monkeypatch) -> None:
    application = create_app()
    service = MagicMock()
    service.login = AsyncMock()
    session = active_session()
    service.login.return_value = LoginResult("session-secret", "csrf-secret", session)
    application.dependency_overrides[get_admin_auth_service] = lambda: service
    production_settings = Settings(
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="rus_map",
        postgres_user="rus_map",
        postgres_password=SecretStr("secret"),
        admin_cookie_secure=True,
        admin_cookie_path="/rus-map",
    )
    monkeypatch.setattr(admin_auth_routes, "get_settings", lambda: production_settings)

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/admin/auth/login",
            json={"username": "editor", "password": "secret password"},
        )

    assert response.status_code == 200
    assert response.json()["admin"] == {
        "id": str(session.admin_id),
        "username": "editor",
    }
    cookies = response.headers.get_list("set-cookie")
    session_cookie = next(
        cookie for cookie in cookies if "rus_map_admin_session" in cookie
    )
    csrf_cookie = next(cookie for cookie in cookies if "rus_map_admin_csrf" in cookie)
    assert "HttpOnly" in session_cookie
    assert "Secure" in session_cookie
    assert "SameSite=strict" in session_cookie
    assert "Path=/rus-map" in session_cookie
    assert "HttpOnly" not in csrf_cookie
    assert "Secure" in csrf_cookie
    assert response.headers["cache-control"] == "no-store"


def test_bad_username_and_password_have_identical_response() -> None:
    bodies = []
    for username in ("known", "unknown"):
        application = create_app()
        service = MagicMock()
        service.login = AsyncMock()
        service.login.side_effect = InvalidCredentialsError
        application.dependency_overrides[get_admin_auth_service] = (
            lambda service=service: service
        )
        with TestClient(application) as client:
            response = client.post(
                "/api/v1/admin/auth/login",
                json={"username": username, "password": "wrong"},
            )
        bodies.append((response.status_code, response.json()))

    assert (
        bodies[0]
        == bodies[1]
        == (
            401,
            {"detail": "Incorrect username or password"},
        )
    )


def test_me_requires_authentication_and_returns_current_admin() -> None:
    unauthenticated = create_app()
    auth_service = MagicMock()
    auth_service.authenticate = AsyncMock(side_effect=InvalidCredentialsError)
    unauthenticated.dependency_overrides[get_admin_auth_service] = lambda: auth_service
    with TestClient(unauthenticated) as client:
        response = client.get("/api/v1/admin/auth/me")
    assert response.status_code == 401

    application = create_app()
    session = active_session()
    application.dependency_overrides[get_current_admin_session] = lambda: session
    with TestClient(application) as client:
        response = client.get("/api/v1/admin/auth/me")
    assert response.status_code == 200
    assert response.json() == {"id": str(session.admin_id), "username": "editor"}


def test_logout_requires_csrf_and_revokes_session() -> None:
    application = create_app()
    session = active_session()
    service = MagicMock()
    service.logout = AsyncMock()
    service.verify_csrf.side_effect = InvalidCredentialsError
    application.dependency_overrides[get_current_admin_session] = lambda: session
    application.dependency_overrides[get_admin_auth_service] = lambda: service

    with TestClient(application) as client:
        rejected = client.post("/api/v1/admin/auth/logout")
        service.verify_csrf.side_effect = None
        accepted = client.post(
            "/api/v1/admin/auth/logout", headers={"X-CSRF-Token": "csrf"}
        )

    assert rejected.status_code == 403
    assert accepted.status_code == 204
    service.logout.assert_awaited_once_with(session)
