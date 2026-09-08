import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from pwdlib import PasswordHash

from rus_map.config import Settings
from rus_map.repositories.auth import AdminAuthRepository, AuthenticatedSession

password_hasher = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$wagCPXjifgvUFBzq4hqe3w$"
    "CYaIb8sB+wtD+Vu/P4uod1+Qof8h+1g7bbDlBID48Rc"
)


class InvalidCredentialsError(Exception):
    """Credentials do not identify an active administrator."""


class LoginRateLimitedError(Exception):
    """A persistent login throttle currently blocks this attempt."""


@dataclass(frozen=True, slots=True)
class LoginResult:
    session_token: str
    csrf_token: str
    session: AuthenticatedSession


def normalize_username(username: str) -> str:
    return username.strip().lower()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def throttle_keys(username: str, client_address: str) -> tuple[str, str]:
    return (
        hash_token(f"username:{normalize_username(username)}"),
        hash_token(f"client:{client_address}"),
    )


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


class AdminAuthService:
    """Authenticate administrators and manage opaque server-side sessions."""

    def __init__(self, repository: AdminAuthRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    async def login(
        self, username: str, password: str, client_address: str
    ) -> LoginResult:
        now = datetime.now(UTC)
        normalized = normalize_username(username)
        keys = throttle_keys(normalized, client_address)
        if await self._repository.any_throttle_blocked(keys, now):
            raise LoginRateLimitedError

        admin = await self._repository.get_admin_by_username(normalized)
        candidate_hash = (
            admin.password_hash if admin is not None else DUMMY_PASSWORD_HASH
        )
        password_matches = password_hasher.verify(password, candidate_hash)
        if admin is None or not admin.is_active or not password_matches:
            await self._repository.record_failed_attempt(
                keys,
                now,
                timedelta(minutes=self._settings.admin_login_window_minutes),
                timedelta(minutes=self._settings.admin_login_block_minutes),
                self._settings.admin_login_max_failures,
            )
            await self._repository.commit_failed_attempt()
            raise InvalidCredentialsError

        await self._repository.clear_throttles(keys)
        session_token = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        expires_at = now + timedelta(hours=self._settings.admin_session_ttl_hours)
        session_id = await self._repository.create_session(
            admin.id,
            hash_token(session_token),
            hash_token(csrf_token),
            expires_at,
        )
        return LoginResult(
            session_token=session_token,
            csrf_token=csrf_token,
            session=AuthenticatedSession(
                session_id=session_id,
                admin_id=admin.id,
                username=admin.username,
                csrf_token_hash=hash_token(csrf_token),
                expires_at=expires_at,
            ),
        )

    async def authenticate(self, session_token: str | None) -> AuthenticatedSession:
        if not session_token:
            raise InvalidCredentialsError
        session = await self._repository.get_active_session(
            hash_token(session_token), datetime.now(UTC)
        )
        if session is None:
            raise InvalidCredentialsError
        return session

    def verify_csrf(
        self, session: AuthenticatedSession, csrf_token: str | None
    ) -> None:
        if not csrf_token or not hmac.compare_digest(
            session.csrf_token_hash, hash_token(csrf_token)
        ):
            raise InvalidCredentialsError

    async def logout(self, session: AuthenticatedSession) -> None:
        await self._repository.revoke_session(session.session_id, datetime.now(UTC))
