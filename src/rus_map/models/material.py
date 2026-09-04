from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from rus_map.db.base import Base


class MaterialType(StrEnum):
    """Supported kinds of information attached to a place."""

    TEXT = "text"
    EXTERNAL_LINK = "external_link"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class ModerationStatus(StrEnum):
    """Lifecycle states used by the moderation workflow."""

    PENDING_REVIEW = "pending_review"
    PUBLISHED = "published"
    REJECTED = "rejected"
    ARCHIVED = "archived"


def enum_values(enum_class: type[StrEnum]) -> list[str]:
    """Store stable enum values rather than Python member names."""
    return [member.value for member in enum_class]


class Material(Base):
    """A moderated piece of information linked to one place."""

    __tablename__ = "materials"
    __table_args__ = (
        CheckConstraint(
            "type IN ('text', 'external_link', 'image', 'video', 'audio')",
            name="ck_materials_type",
        ),
        CheckConstraint(
            "status IN ('pending_review', 'published', 'rejected', 'archived')",
            name="ck_materials_status",
        ),
        CheckConstraint(
            "char_length(btrim(title)) > 0",
            name="ck_materials_title_not_blank",
        ),
        Index("idx_materials_place_status", "place_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    place_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.places.id"),
        nullable=False,
    )
    type: Mapped[MaterialType] = mapped_column(
        Enum(
            MaterialType,
            name="material_type",
            native_enum=False,
            create_constraint=False,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    status: Mapped[ModerationStatus] = mapped_column(
        Enum(
            ModerationStatus,
            name="moderation_status",
            native_enum=False,
            create_constraint=False,
            values_callable=enum_values,
        ),
        nullable=False,
        default=ModerationStatus.PENDING_REVIEW,
        server_default=ModerationStatus.PENDING_REVIEW.value,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    source: Mapped[str | None] = mapped_column(String(500), nullable=True)
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


class MaterialRevision(Base):
    """An immutable version of a material's text or URL."""

    __tablename__ = "material_revisions"
    __table_args__ = (
        CheckConstraint(
            "revision_number > 0",
            name="ck_material_revisions_number_positive",
        ),
        CheckConstraint(
            "(content IS NOT NULL) <> (url IS NOT NULL)",
            name="ck_material_revisions_exactly_one_value",
        ),
        CheckConstraint(
            "content IS NULL OR char_length(btrim(content)) > 0",
            name="ck_material_revisions_content_not_blank",
        ),
        CheckConstraint(
            "url IS NULL OR url ~* '^https?://'",
            name="ck_material_revisions_http_url",
        ),
        UniqueConstraint(
            "material_id",
            "revision_number",
            name="uq_material_revisions_material_number",
        ),
        CheckConstraint(
            "status IN ('pending_review', 'published', 'rejected', 'archived')",
            name="ck_material_revisions_status",
        ),
        Index(
            "idx_material_revisions_material_status_number",
            "material_id",
            "status",
            "revision_number",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    material_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.materials.id"),
        nullable=False,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ModerationStatus] = mapped_column(
        Enum(
            ModerationStatus,
            name="moderation_status",
            native_enum=False,
            create_constraint=False,
            values_callable=enum_values,
        ),
        nullable=False,
        default=ModerationStatus.PENDING_REVIEW,
        server_default=ModerationStatus.PENDING_REVIEW.value,
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
