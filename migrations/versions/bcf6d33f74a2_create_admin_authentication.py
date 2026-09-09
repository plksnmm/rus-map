"""create administrator authentication

Revision ID: bcf6d33f74a2
Revises: 7b82e019c4a6
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "bcf6d33f74a2"
down_revision: str | None = "7b82e019c4a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "admin_users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "username = lower(btrim(username)) AND char_length(username) > 0",
            name="ck_admin_users_normalized_username",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        schema="app",
    )
    op.create_table(
        "admin_login_throttles",
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "failed_attempts >= 0", name="ck_admin_login_throttles_failures"
        ),
        sa.PrimaryKeyConstraint("key_hash"),
        schema="app",
    )
    op.create_index(
        "idx_admin_login_throttles_updated",
        "admin_login_throttles",
        ["updated_at"],
        schema="app",
    )
    op.create_table(
        "admin_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("admin_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["admin_id"],
            ["app.admin_users.id"],
            name="fk_admin_sessions_admin_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
        schema="app",
    )
    op.create_index(
        "idx_admin_sessions_admin_expires",
        "admin_sessions",
        ["admin_id", "expires_at"],
        schema="app",
    )
    op.create_index(
        "idx_admin_sessions_expires",
        "admin_sessions",
        ["expires_at"],
        schema="app",
    )


def downgrade() -> None:
    op.drop_index(
        "idx_admin_sessions_expires", table_name="admin_sessions", schema="app"
    )
    op.drop_index(
        "idx_admin_sessions_admin_expires", table_name="admin_sessions", schema="app"
    )
    op.drop_table("admin_sessions", schema="app")
    op.drop_index(
        "idx_admin_login_throttles_updated",
        table_name="admin_login_throttles",
        schema="app",
    )
    op.drop_table("admin_login_throttles", schema="app")
    op.drop_table("admin_users", schema="app")
