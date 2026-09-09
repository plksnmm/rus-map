from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from rus_map.models import AdminLoginThrottle, AdminSession, AdminUser


@dataclass(frozen=True, slots=True)
class AdminRecord:
    id: UUID
    username: str
    password_hash: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    session_id: UUID
    admin_id: UUID
    username: str
    csrf_token_hash: str
    expires_at: datetime


class AdminAuthRepository:
    """Persistence operations used by administrator authentication."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_admin_by_username(self, username: str) -> AdminRecord | None:
        row = (
            (
                await self._session.execute(
                    select(
                        AdminUser.id,
                        AdminUser.username,
                        AdminUser.password_hash,
                        AdminUser.is_active,
                    ).where(AdminUser.username == username)
                )
            )
            .tuples()
            .one_or_none()
        )
        return None if row is None else AdminRecord(*row)

    async def create_admin(self, username: str, password_hash: str) -> AdminRecord:
        row = (
            (
                await self._session.execute(
                    insert(AdminUser)
                    .values(id=uuid4(), username=username, password_hash=password_hash)
                    .returning(
                        AdminUser.id,
                        AdminUser.username,
                        AdminUser.password_hash,
                        AdminUser.is_active,
                    )
                )
            )
            .tuples()
            .one()
        )
        return AdminRecord(*row)

    async def create_session(
        self,
        admin_id: UUID,
        token_hash: str,
        csrf_token_hash: str,
        expires_at: datetime,
    ) -> UUID:
        session_id = uuid4()
        await self._session.execute(
            insert(AdminSession).values(
                id=session_id,
                admin_id=admin_id,
                token_hash=token_hash,
                csrf_token_hash=csrf_token_hash,
                expires_at=expires_at,
                last_used_at=datetime.now(UTC),
            )
        )
        return session_id

    async def get_active_session(
        self, token_hash: str, now: datetime
    ) -> AuthenticatedSession | None:
        row = (
            (
                await self._session.execute(
                    select(
                        AdminSession.id,
                        AdminUser.id,
                        AdminUser.username,
                        AdminSession.csrf_token_hash,
                        AdminSession.expires_at,
                    )
                    .join(AdminUser, AdminUser.id == AdminSession.admin_id)
                    .where(
                        AdminSession.token_hash == token_hash,
                        AdminSession.revoked_at.is_(None),
                        AdminSession.expires_at > now,
                        AdminUser.is_active.is_(True),
                    )
                )
            )
            .tuples()
            .one_or_none()
        )
        if row is None:
            return None
        await self._session.execute(
            update(AdminSession)
            .where(AdminSession.id == row[0])
            .values(last_used_at=now)
        )
        return AuthenticatedSession(*row)

    async def revoke_session(self, session_id: UUID, now: datetime) -> None:
        await self._session.execute(
            update(AdminSession)
            .where(AdminSession.id == session_id, AdminSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    async def any_throttle_blocked(
        self, key_hashes: tuple[str, ...], now: datetime
    ) -> bool:
        blocked = await self._session.scalar(
            select(AdminLoginThrottle.key_hash)
            .where(
                AdminLoginThrottle.key_hash.in_(key_hashes),
                AdminLoginThrottle.blocked_until > now,
            )
            .limit(1)
        )
        return blocked is not None

    async def record_failed_attempt(
        self,
        key_hashes: tuple[str, ...],
        now: datetime,
        window: timedelta,
        block_for: timedelta,
        max_failures: int,
    ) -> None:
        for key_hash in key_hashes:
            await self._session.execute(
                pg_insert(AdminLoginThrottle)
                .values(
                    key_hash=key_hash,
                    failed_attempts=0,
                    window_started_at=now,
                    updated_at=now,
                )
                .on_conflict_do_nothing(index_elements=[AdminLoginThrottle.key_hash])
            )

        rows = (
            (
                await self._session.execute(
                    select(AdminLoginThrottle)
                    .where(AdminLoginThrottle.key_hash.in_(key_hashes))
                    .order_by(AdminLoginThrottle.key_hash)
                    .with_for_update()
                )
            )
            .scalars()
            .all()
        )
        for bucket in rows:
            if now - bucket.window_started_at >= window:
                bucket.window_started_at = now
                bucket.failed_attempts = 1
            else:
                bucket.failed_attempts += 1
            bucket.blocked_until = (
                now + block_for if bucket.failed_attempts >= max_failures else None
            )
            bucket.updated_at = now

    async def clear_throttles(self, key_hashes: tuple[str, ...]) -> None:
        await self._session.execute(
            delete(AdminLoginThrottle).where(
                AdminLoginThrottle.key_hash.in_(key_hashes)
            )
        )

    async def commit_failed_attempt(self) -> None:
        """Persist throttling even though the HTTP authentication request fails."""
        await self._session.commit()
