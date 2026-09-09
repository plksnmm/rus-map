from fastapi import APIRouter, HTTPException, Request, Response, status

from rus_map.api.dependencies import (
    AdminAuthServiceDependency,
    AdminSessionDependency,
    CsrfAdminSessionDependency,
)
from rus_map.config import get_settings
from rus_map.schemas.auth import AdminLoginRequest, AdminLoginResponse, AdminResponse
from rus_map.services.auth import (
    InvalidCredentialsError,
    LoginRateLimitedError,
)

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])
INVALID_CREDENTIALS = "Incorrect username or password"


def client_address(request: Request) -> str:
    """Read the client address forwarded by the loopback-only Caddy proxy."""
    return request.headers.get("x-real-ip") or (
        request.client.host if request.client else "unknown"
    )


def set_auth_cookies(response: Response, session_token: str, csrf_token: str) -> None:
    settings = get_settings()
    max_age = settings.admin_session_ttl_hours * 60 * 60
    response.set_cookie(
        settings.admin_session_cookie_name,
        session_token,
        max_age=max_age,
        secure=settings.admin_cookie_secure,
        samesite="strict",
        path=settings.admin_cookie_path,
        httponly=True,
    )
    response.set_cookie(
        settings.admin_csrf_cookie_name,
        csrf_token,
        max_age=max_age,
        secure=settings.admin_cookie_secure,
        samesite="strict",
        path=settings.admin_cookie_path,
        httponly=False,
    )
    response.headers["Cache-Control"] = "no-store"


def clear_auth_cookies(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        settings.admin_session_cookie_name,
        path=settings.admin_cookie_path,
        secure=settings.admin_cookie_secure,
        httponly=True,
        samesite="strict",
    )
    response.delete_cookie(
        settings.admin_csrf_cookie_name,
        path=settings.admin_cookie_path,
        secure=settings.admin_cookie_secure,
        httponly=False,
        samesite="strict",
    )
    response.headers["Cache-Control"] = "no-store"


@router.post("/login", response_model=AdminLoginResponse)
async def login(
    credentials: AdminLoginRequest,
    request: Request,
    response: Response,
    service: AdminAuthServiceDependency,
) -> AdminLoginResponse:
    try:
        result = await service.login(
            credentials.username,
            credentials.password,
            client_address(request),
        )
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS,
        ) from error
    except LoginRateLimitedError as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts",
            headers={"Retry-After": str(get_settings().admin_login_block_minutes * 60)},
        ) from error

    set_auth_cookies(response, result.session_token, result.csrf_token)
    return AdminLoginResponse(
        admin=AdminResponse(
            id=result.session.admin_id,
            username=result.session.username,
        ),
        expires_at=result.session.expires_at,
    )


@router.get("/me", response_model=AdminResponse)
async def current_admin(
    response: Response, session: AdminSessionDependency
) -> AdminResponse:
    response.headers["Cache-Control"] = "no-store"
    return AdminResponse(id=session.admin_id, username=session.username)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    session: CsrfAdminSessionDependency,
    service: AdminAuthServiceDependency,
) -> None:
    await service.logout(session)
    clear_auth_cookies(response)
