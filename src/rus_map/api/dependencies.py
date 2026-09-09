from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from rus_map.config import get_settings
from rus_map.db.session import get_session
from rus_map.repositories.auth import AdminAuthRepository, AuthenticatedSession
from rus_map.repositories.material import MaterialRepository
from rus_map.repositories.place import PlaceRepository
from rus_map.repositories.submission import PlaceSubmissionRepository
from rus_map.services.auth import AdminAuthService, InvalidCredentialsError
from rus_map.services.submission import PlaceSubmissionService

SessionDependency = Annotated[AsyncSession, Depends(get_session)]


def get_place_repository(session: SessionDependency) -> PlaceRepository:
    """Build a place repository for the current database session."""
    return PlaceRepository(session)


PlaceRepositoryDependency = Annotated[
    PlaceRepository,
    Depends(get_place_repository),
]


def get_material_repository(session: SessionDependency) -> MaterialRepository:
    """Build a material repository for the current database session."""
    return MaterialRepository(session)


MaterialRepositoryDependency = Annotated[
    MaterialRepository,
    Depends(get_material_repository),
]


def get_place_submission_repository(
    session: SessionDependency,
) -> PlaceSubmissionRepository:
    return PlaceSubmissionRepository(session)


PlaceSubmissionRepositoryDependency = Annotated[
    PlaceSubmissionRepository, Depends(get_place_submission_repository)
]


def get_place_submission_service(
    submissions: PlaceSubmissionRepositoryDependency,
    places: PlaceRepositoryDependency,
) -> PlaceSubmissionService:
    return PlaceSubmissionService(submissions, places)


PlaceSubmissionServiceDependency = Annotated[
    PlaceSubmissionService, Depends(get_place_submission_service)
]


def get_admin_auth_repository(session: SessionDependency) -> AdminAuthRepository:
    return AdminAuthRepository(session)


AdminAuthRepositoryDependency = Annotated[
    AdminAuthRepository, Depends(get_admin_auth_repository)
]


def get_admin_auth_service(
    repository: AdminAuthRepositoryDependency,
) -> AdminAuthService:
    return AdminAuthService(repository, get_settings())


AdminAuthServiceDependency = Annotated[
    AdminAuthService, Depends(get_admin_auth_service)
]


async def get_current_admin_session(
    request: Request,
    service: AdminAuthServiceDependency,
) -> AuthenticatedSession:
    settings = get_settings()
    try:
        return await service.authenticate(
            request.cookies.get(settings.admin_session_cookie_name)
        )
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        ) from error


AdminSessionDependency = Annotated[
    AuthenticatedSession, Depends(get_current_admin_session)
]


async def get_csrf_protected_admin_session(
    session: AdminSessionDependency,
    service: AdminAuthServiceDependency,
    csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> AuthenticatedSession:
    """Require a session-bound CSRF token for administrative mutations."""
    try:
        service.verify_csrf(session, csrf_token)
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed",
        ) from error
    return session


CsrfAdminSessionDependency = Annotated[
    AuthenticatedSession, Depends(get_csrf_protected_admin_session)
]
