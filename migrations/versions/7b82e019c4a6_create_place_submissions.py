"""create place submissions

Revision ID: 7b82e019c4a6
Revises: f3c94f602a18
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7b82e019c4a6"
down_revision: str | None = "f3c94f602a18"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "place_submissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=8),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column(
            "source_urls",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("approved_place_id", sa.Uuid(), nullable=True),
        sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True),
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
            "latitude BETWEEN -90 AND 90",
            name="ck_place_submissions_latitude",
        ),
        sa.CheckConstraint(
            "longitude BETWEEN -180 AND 180",
            name="ck_place_submissions_longitude",
        ),
        sa.CheckConstraint(
            "(status = 'pending' AND approved_place_id IS NULL "
            "AND moderated_at IS NULL) OR "
            "(status = 'approved' AND approved_place_id IS NOT NULL "
            "AND moderated_at IS NOT NULL) OR "
            "(status = 'rejected' AND approved_place_id IS NULL "
            "AND moderated_at IS NOT NULL)",
            name="ck_place_submissions_moderation_result",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_place_submissions_status",
        ),
        sa.CheckConstraint(
            "char_length(btrim(title)) > 0",
            name="ck_place_submissions_title_not_blank",
        ),
        sa.ForeignKeyConstraint(
            ["approved_place_id"],
            ["app.places.id"],
            name="fk_place_submissions_approved_place_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("approved_place_id"),
        schema="app",
    )
    op.create_index(
        "idx_place_submissions_status_created",
        "place_submissions",
        ["status", "created_at"],
        unique=False,
        schema="app",
    )


def downgrade() -> None:
    op.drop_index(
        "idx_place_submissions_status_created",
        table_name="place_submissions",
        schema="app",
    )
    op.drop_table("place_submissions", schema="app")
