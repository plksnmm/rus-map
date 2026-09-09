from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from rus_map.db.base import Base
from rus_map.models.material import enum_values


class SubmissionStatus(StrEnum):
    """Lifecycle states of a proposed place."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PlaceSubmission(Base):
    """An untrusted place proposal kept outside the public places table."""

    __tablename__ = "place_submissions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_place_submissions_status",
        ),
        CheckConstraint(
            "char_length(btrim(title)) > 0",
            name="ck_place_submissions_title_not_blank",
        ),
        CheckConstraint(
            "latitude BETWEEN -90 AND 90",
            name="ck_place_submissions_latitude",
        ),
        CheckConstraint(
            "longitude BETWEEN -180 AND 180",
            name="ck_place_submissions_longitude",
        ),
        CheckConstraint(
            "(status = 'pending' AND approved_place_id IS NULL "
            "AND moderated_by_admin_id IS NULL AND moderated_at IS NULL) OR "
            "(status = 'approved' AND approved_place_id IS NOT NULL "
            "AND moderated_at IS NOT NULL) OR "
            "(status = 'rejected' AND approved_place_id IS NULL "
            "AND moderated_at IS NOT NULL)",
            name="ck_place_submissions_moderation_result",
        ),
        Index(
            "idx_place_submissions_status_created",
            "status",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(
            SubmissionStatus,
            name="submission_status",
            native_enum=False,
            create_constraint=False,
            values_callable=enum_values,
        ),
        nullable=False,
        default=SubmissionStatus.PENDING,
        server_default=SubmissionStatus.PENDING.value,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    source_urls: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_place_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("app.places.id"),
        nullable=True,
        unique=True,
    )
    moderated_by_admin_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("app.admin_users.id"),
        nullable=True,
    )
    moderated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
