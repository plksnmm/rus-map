import argparse
import asyncio
import hashlib
import io
import mimetypes
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal
from urllib.parse import urlsplit
from uuid import UUID

from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rus_map.config import get_settings
from rus_map.db.session import get_engine, get_session_factory
from rus_map.models import (
    Material,
    MaterialRevision,
    MaterialType,
    MediaAsset,
    ModerationStatus,
    Place,
)

Title = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
Source = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]
Url = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2048)
]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]

MAX_SOURCE_BYTES = 25 * 1024 * 1024
MAX_IMAGE_PIXELS = 50_000_000
MAX_DISPLAY_DIMENSION = 1920
ALLOWED_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


class ImageManifestItem(BaseModel):
    """One reviewed image, its material and its first immutable revision."""

    model_config = ConfigDict(extra="forbid")

    media_id: UUID
    material_id: UUID
    revision_id: UUID
    revision_number: int = Field(default=1, gt=0)
    status: ModerationStatus = ModerationStatus.PENDING_REVIEW
    title: Title
    source: Source | None = None
    source_url: Url
    file: str = Field(min_length=1, max_length=500)
    sha256: Sha256

    @model_validator(mode="after")
    def validate_source(self) -> "ImageManifestItem":
        parsed = urlsplit(self.source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("source_url must use HTTP(S) and include a host")
        path = PurePosixPath(self.file.replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("file must be a safe relative path")
        return self


class PlaceImagesManifest(BaseModel):
    """Versioned JSON document accepted by the image importer."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    place_id: UUID
    images: list[ImageManifestItem] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "PlaceImagesManifest":
        for attribute in ("media_id", "material_id", "revision_id"):
            values = [getattr(image, attribute) for image in self.images]
            if len(values) != len(set(values)):
                raise ValueError(f"{attribute} values must be unique")
        return self


@dataclass(frozen=True, slots=True)
class PreparedImage:
    manifest: ImageManifestItem
    original_filename: str
    original_content_type: str
    original_bytes: bytes
    display_bytes: bytes
    display_sha256: str
    width: int
    height: int
    original_storage_key: str
    display_storage_key: str


@dataclass(frozen=True, slots=True)
class ImportResult:
    created_assets: int = 0
    existing_assets: int = 0
    created_materials: int = 0
    existing_materials: int = 0
    created_revisions: int = 0
    existing_revisions: int = 0


class ImageImportError(Exception):
    """An expected validation or idempotency failure."""


def _safe_input_path(assets_dir: Path, filename: str) -> Path:
    root = assets_dir.resolve()
    path = (root / filename).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ImageImportError(
            f"image file not found inside assets directory: {filename}"
        )
    return path


def prepare_image(item: ImageManifestItem, assets_dir: Path) -> PreparedImage:
    """Validate an original and create its deterministic web representation."""
    path = _safe_input_path(assets_dir, item.file)
    original_bytes = path.read_bytes()
    if not original_bytes or len(original_bytes) > MAX_SOURCE_BYTES:
        raise ImageImportError(f"image {item.file} must be between 1 byte and 25 MiB")
    actual_hash = hashlib.sha256(original_bytes).hexdigest()
    if actual_hash != item.sha256:
        raise ImageImportError(f"SHA-256 mismatch for {item.file}: got {actual_hash}")

    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    try:
        with Image.open(io.BytesIO(original_bytes)) as opened:
            opened.load()
            if opened.format not in ALLOWED_FORMATS:
                raise ImageImportError(f"unsupported image format for {item.file}")
            original_content_type = ALLOWED_FORMATS[opened.format]
            image = ImageOps.exif_transpose(opened)
            image.thumbnail(
                (MAX_DISPLAY_DIMENSION, MAX_DISPLAY_DIMENSION),
                Image.Resampling.LANCZOS,
            )
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA" if "transparency" in image.info else "RGB")
            width, height = image.size
            output = io.BytesIO()
            image.save(output, format="WEBP", quality=84, method=6)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ImageImportError(f"invalid image {item.file}: {error}") from error

    display_bytes = output.getvalue()
    suffix = mimetypes.guess_extension(original_content_type) or path.suffix.lower()
    return PreparedImage(
        manifest=item,
        original_filename=path.name,
        original_content_type=original_content_type,
        original_bytes=original_bytes,
        display_bytes=display_bytes,
        display_sha256=hashlib.sha256(display_bytes).hexdigest(),
        width=width,
        height=height,
        original_storage_key=f"original/{item.media_id}{suffix}",
        display_storage_key=f"display/{item.media_id}.webp",
    )


def _asset_matches(asset: MediaAsset, prepared: PreparedImage) -> bool:
    return (
        asset.sha256 == prepared.manifest.sha256
        and asset.display_sha256 == prepared.display_sha256
        and asset.original_storage_key == prepared.original_storage_key
        and asset.display_storage_key == prepared.display_storage_key
        and asset.original_filename == prepared.original_filename
        and asset.original_content_type == prepared.original_content_type
        and asset.original_byte_size == len(prepared.original_bytes)
        and asset.display_content_type == "image/webp"
        and asset.display_byte_size == len(prepared.display_bytes)
        and asset.width == prepared.width
        and asset.height == prepared.height
    )


async def import_place_images(
    session: AsyncSession,
    manifest: PlaceImagesManifest,
    prepared_images: list[PreparedImage],
) -> ImportResult:
    """Stage image metadata, materials and revisions in one transaction."""
    if await session.get(Place, manifest.place_id) is None:
        raise ImageImportError(f"place {manifest.place_id} does not exist")

    counts = [0, 0, 0, 0, 0, 0]
    for prepared in prepared_images:
        item = prepared.manifest
        asset = await session.get(MediaAsset, item.media_id)
        same_hash_id = await session.scalar(
            select(MediaAsset.id).where(MediaAsset.sha256 == item.sha256)
        )
        if asset is None:
            if same_hash_id is not None:
                raise ImageImportError(
                    f"image hash already belongs to media asset {same_hash_id}"
                )
            session.add(
                MediaAsset(
                    id=item.media_id,
                    sha256=item.sha256,
                    display_sha256=prepared.display_sha256,
                    original_storage_key=prepared.original_storage_key,
                    display_storage_key=prepared.display_storage_key,
                    original_filename=prepared.original_filename,
                    original_content_type=prepared.original_content_type,
                    original_byte_size=len(prepared.original_bytes),
                    display_content_type="image/webp",
                    display_byte_size=len(prepared.display_bytes),
                    width=prepared.width,
                    height=prepared.height,
                )
            )
            counts[0] += 1
        elif not _asset_matches(asset, prepared):
            raise ImageImportError(
                f"media asset {item.media_id} conflicts with stored data"
            )
        else:
            counts[1] += 1

        material = await session.get(Material, item.material_id)
        if material is None:
            session.add(
                Material(
                    id=item.material_id,
                    place_id=manifest.place_id,
                    type=MaterialType.IMAGE,
                    status=item.status,
                    title=item.title,
                    source=item.source,
                )
            )
            counts[2] += 1
        elif not (
            material.place_id == manifest.place_id
            and material.type == MaterialType.IMAGE
            and material.status == item.status
            and material.title == item.title
            and material.source == item.source
        ):
            raise ImageImportError(
                f"material {item.material_id} conflicts with stored data"
            )
        else:
            counts[3] += 1

        revision = await session.get(MaterialRevision, item.revision_id)
        if revision is None:
            existing_number = await session.scalar(
                select(MaterialRevision.id).where(
                    MaterialRevision.material_id == item.material_id,
                    MaterialRevision.revision_number == item.revision_number,
                )
            )
            if existing_number is not None:
                raise ImageImportError(
                    f"revision number already belongs to {existing_number}"
                )
            session.add(
                MaterialRevision(
                    id=item.revision_id,
                    material_id=item.material_id,
                    revision_number=item.revision_number,
                    status=item.status,
                    content=None,
                    url=item.source_url,
                    media_asset_id=item.media_id,
                )
            )
            counts[4] += 1
        elif not (
            revision.material_id == item.material_id
            and revision.revision_number == item.revision_number
            and revision.status == item.status
            and revision.content is None
            and revision.url == item.source_url
            and revision.media_asset_id == item.media_id
        ):
            raise ImageImportError(
                f"revision {item.revision_id} conflicts with stored data"
            )
        else:
            counts[5] += 1

    await session.flush()
    return ImportResult(*counts)


def _write_file(root: Path, key: str, data: bytes, expected_hash: str) -> bool:
    path = (root / key).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ImageImportError("unsafe media storage key")
    if path.exists():
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            raise ImageImportError(
                f"stored file conflicts with expected content: {key}"
            )
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return True


async def execute_import(
    manifest: PlaceImagesManifest,
    *,
    assets_dir: Path,
    media_root: Path,
    dry_run: bool,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> ImportResult:
    prepared = [prepare_image(item, assets_dir) for item in manifest.images]
    factory = session_factory or get_session_factory()
    created_paths: list[Path] = []
    async with factory() as session:
        try:
            result = await import_place_images(session, manifest, prepared)
            if dry_run:
                await session.rollback()
                return result
            root = media_root.resolve()
            root.mkdir(parents=True, exist_ok=True)
            for image in prepared:
                for key, data, digest in (
                    (
                        image.original_storage_key,
                        image.original_bytes,
                        image.manifest.sha256,
                    ),
                    (
                        image.display_storage_key,
                        image.display_bytes,
                        image.display_sha256,
                    ),
                ):
                    if _write_file(root, key, data, digest):
                        created_paths.append(root / key)
            await session.commit()
            return result
        except BaseException:
            await session.rollback()
            for path in created_paths:
                path.unlink(missing_ok=True)
            raise


def load_manifest(filename: str) -> PlaceImagesManifest:
    raw = sys.stdin.read() if filename == "-" else Path(filename).read_text("utf-8")
    return PlaceImagesManifest.model_validate_json(raw)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import reviewed place images and optimize them for the web."
    )
    parser.add_argument(
        "--file", required=True, help="UTF-8 JSON manifest path, or - for stdin."
    )
    parser.add_argument(
        "--assets-dir",
        required=True,
        type=Path,
        help="Directory containing source images.",
    )
    parser.add_argument(
        "--media-root", type=Path, help="Override persistent media storage directory."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and roll back all database changes.",
    )
    return parser


async def async_main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        manifest = load_manifest(arguments.file)
        result = await execute_import(
            manifest,
            assets_dir=arguments.assets_dir,
            media_root=arguments.media_root or get_settings().media_root,
            dry_run=arguments.dry_run,
        )
    except (OSError, ValueError, ImageImportError) as error:
        print(f"Import failed: {error}", file=sys.stderr)
        return 1
    finally:
        await get_engine().dispose()

    mode = "Dry run" if arguments.dry_run else "Import"
    print(
        f"{mode} successful: assets created={result.created_assets}, already existed={result.existing_assets}; "
        f"materials created={result.created_materials}, already existed={result.existing_materials}; "
        f"revisions created={result.created_revisions}, already existed={result.existing_revisions}."
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
