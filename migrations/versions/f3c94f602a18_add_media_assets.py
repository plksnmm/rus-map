"""add media assets

Revision ID: f3c94f602a18
Revises: 28388488c1fd
Create Date: 2026-09-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f3c94f602a18"
down_revision: str | None = "28388488c1fd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("display_sha256", sa.String(length=64), nullable=False),
        sa.Column("original_storage_key", sa.String(length=500), nullable=False),
        sa.Column("display_storage_key", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("original_content_type", sa.String(length=100), nullable=False),
        sa.Column("original_byte_size", sa.BigInteger(), nullable=False),
        sa.Column("display_content_type", sa.String(length=100), nullable=False),
        sa.Column("display_byte_size", sa.BigInteger(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "display_byte_size > 0", name="ck_media_assets_display_size"
        ),
        sa.CheckConstraint(
            "width > 0 AND height > 0", name="ck_media_assets_dimensions"
        ),
        sa.CheckConstraint(
            "original_byte_size > 0", name="ck_media_assets_original_size"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("display_storage_key"),
        sa.UniqueConstraint("original_storage_key"),
        sa.UniqueConstraint("sha256"),
        schema="app",
    )
    op.add_column(
        "material_revisions",
        sa.Column("media_asset_id", sa.Uuid(), nullable=True),
        schema="app",
    )
    op.create_foreign_key(
        "fk_material_revisions_media_asset_id",
        "material_revisions",
        "media_assets",
        ["media_asset_id"],
        ["id"],
        source_schema="app",
        referent_schema="app",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_material_revisions_media_asset_id",
        "material_revisions",
        schema="app",
        type_="foreignkey",
    )
    op.drop_column("material_revisions", "media_asset_id", schema="app")
    op.drop_table("media_assets", schema="app")
