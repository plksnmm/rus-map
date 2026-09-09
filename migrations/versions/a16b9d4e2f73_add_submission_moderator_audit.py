"""add submission moderator audit

Revision ID: a16b9d4e2f73
Revises: bcf6d33f74a2
Create Date: 2026-09-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a16b9d4e2f73"
down_revision: str | None = "bcf6d33f74a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_place_submissions_moderation_result",
        "place_submissions",
        schema="app",
        type_="check",
    )
    op.add_column(
        "place_submissions",
        sa.Column("moderated_by_admin_id", sa.Uuid(), nullable=True),
        schema="app",
    )
    op.create_foreign_key(
        "fk_place_submissions_moderated_by_admin_id",
        "place_submissions",
        "admin_users",
        ["moderated_by_admin_id"],
        ["id"],
        source_schema="app",
        referent_schema="app",
    )
    op.create_check_constraint(
        "ck_place_submissions_moderation_result",
        "place_submissions",
        "(status = 'pending' AND approved_place_id IS NULL "
        "AND moderated_by_admin_id IS NULL AND moderated_at IS NULL) OR "
        "(status = 'approved' AND approved_place_id IS NOT NULL "
        "AND moderated_at IS NOT NULL) OR "
        "(status = 'rejected' AND approved_place_id IS NULL "
        "AND moderated_at IS NOT NULL)",
        schema="app",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_place_submissions_moderation_result",
        "place_submissions",
        schema="app",
        type_="check",
    )
    op.drop_constraint(
        "fk_place_submissions_moderated_by_admin_id",
        "place_submissions",
        schema="app",
        type_="foreignkey",
    )
    op.drop_column("place_submissions", "moderated_by_admin_id", schema="app")
    op.create_check_constraint(
        "ck_place_submissions_moderation_result",
        "place_submissions",
        "(status = 'pending' AND approved_place_id IS NULL "
        "AND moderated_at IS NULL) OR "
        "(status = 'approved' AND approved_place_id IS NOT NULL "
        "AND moderated_at IS NOT NULL) OR "
        "(status = 'rejected' AND approved_place_id IS NULL "
        "AND moderated_at IS NOT NULL)",
        schema="app",
    )
