from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Integer,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from rus_map.db.base import Base


class MediaAsset(Base):
    """An original image and its web-optimized representation."""

    __tablename__ = "media_assets"
    __table_args__ = (
        CheckConstraint("original_byte_size > 0", name="ck_media_assets_original_size"),
        CheckConstraint("display_byte_size > 0", name="ck_media_assets_display_size"),
        CheckConstraint("width > 0 AND height > 0", name="ck_media_assets_dimensions"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    display_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    original_storage_key: Mapped[str] = mapped_column(
        String(500), nullable=False, unique=True
    )
    display_storage_key: Mapped[str] = mapped_column(
        String(500), nullable=False, unique=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    original_byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    display_content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    display_byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
