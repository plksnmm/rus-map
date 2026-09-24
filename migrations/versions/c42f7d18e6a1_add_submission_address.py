"""add submission address

Revision ID: c42f7d18e6a1
Revises: a16b9d4e2f73
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c42f7d18e6a1"
down_revision: str | None = "a16b9d4e2f73"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "place_submissions",
        sa.Column("address", sa.String(length=500), nullable=True),
        schema="app",
    )


def downgrade() -> None:
    op.drop_column("place_submissions", "address", schema="app")
