import argparse
import asyncio
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rus_map.db.session import get_engine, get_session_factory
from rus_map.models import (
    Material,
    MaterialRevision,
    MaterialType,
    ModerationStatus,
    Place,
)

Title = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]
Source = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
]
Content = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
Url = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=2048),
]


class RevisionManifest(BaseModel):
    """One immutable revision from an administrative manifest."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    revision_number: int = Field(gt=0)
    status: ModerationStatus = ModerationStatus.PENDING_REVIEW
    content: Content | None = None
    url: Url | None = None

    @model_validator(mode="after")
    def validate_value(self) -> "RevisionManifest":
        """Require exactly one value and a complete HTTP(S) URL."""
        if (self.content is None) == (self.url is None):
            raise ValueError("revision must contain exactly one of content or url")

        if self.url is not None:
            parsed = urlsplit(self.url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("revision URL must use HTTP(S) and include a host")

        return self


class MaterialManifest(BaseModel):
    """One material and all revisions included in an import."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    type: MaterialType
    status: ModerationStatus = ModerationStatus.PENDING_REVIEW
    title: Title
    source: Source | None = None
    revisions: list[RevisionManifest] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_revisions(self) -> "MaterialManifest":
        """Keep revision IDs/numbers unique and values consistent with type."""
        revision_ids = [revision.id for revision in self.revisions]
        revision_numbers = [revision.revision_number for revision in self.revisions]
        if len(revision_ids) != len(set(revision_ids)):
            raise ValueError("revision IDs must be unique within a material")
        if len(revision_numbers) != len(set(revision_numbers)):
            raise ValueError("revision numbers must be unique within a material")

        for revision in self.revisions:
            if self.type is MaterialType.TEXT and revision.content is None:
                raise ValueError("text material revisions must contain content")
            if self.type is not MaterialType.TEXT and revision.url is None:
                raise ValueError("linked material revisions must contain a URL")

        return self


class PlaceMaterialsManifest(BaseModel):
    """Versioned JSON document accepted by the importer."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    place_id: UUID
    materials: list[MaterialManifest] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "PlaceMaterialsManifest":
        """Reject duplicate stable IDs before accessing the database."""
        material_ids = [material.id for material in self.materials]
        if len(material_ids) != len(set(material_ids)):
            raise ValueError("material IDs must be unique")

        revision_ids = [
            revision.id
            for material in self.materials
            for revision in material.revisions
        ]
        if len(revision_ids) != len(set(revision_ids)):
            raise ValueError("revision IDs must be unique across the manifest")

        return self


@dataclass(frozen=True, slots=True)
class ImportResult:
    """Counts produced by an idempotent import."""

    created_materials: int = 0
    existing_materials: int = 0
    created_revisions: int = 0
    existing_revisions: int = 0


class MaterialImportError(Exception):
    """Base class for expected administrative import failures."""


class PlaceNotFoundError(MaterialImportError):
    """The manifest references a place that does not exist."""


class ManifestConflictError(MaterialImportError):
    """A stable UUID or revision number belongs to different data."""


def _material_matches(
    existing: Material, expected: MaterialManifest, place_id: UUID
) -> bool:
    return (
        existing.place_id == place_id
        and existing.type == expected.type
        and existing.status == expected.status
        and existing.title == expected.title
        and existing.source == expected.source
    )


def _revision_matches(
    existing: MaterialRevision,
    expected: RevisionManifest,
    material_id: UUID,
) -> bool:
    return (
        existing.material_id == material_id
        and existing.revision_number == expected.revision_number
        and existing.status == expected.status
        and existing.content == expected.content
        and existing.url == expected.url
    )


async def import_place_materials(
    session: AsyncSession,
    manifest: PlaceMaterialsManifest,
) -> ImportResult:
    """Stage one idempotent manifest in the caller's transaction."""
    if await session.get(Place, manifest.place_id) is None:
        raise PlaceNotFoundError(f"place {manifest.place_id} does not exist")

    created_materials = 0
    existing_materials = 0
    created_revisions = 0
    existing_revisions = 0

    for expected_material in manifest.materials:
        existing_material = await session.get(Material, expected_material.id)
        if existing_material is None:
            session.add(
                Material(
                    id=expected_material.id,
                    place_id=manifest.place_id,
                    type=expected_material.type,
                    status=expected_material.status,
                    title=expected_material.title,
                    source=expected_material.source,
                ),
            )
            created_materials += 1
        else:
            if not _material_matches(
                existing_material,
                expected_material,
                manifest.place_id,
            ):
                raise ManifestConflictError(
                    f"material {expected_material.id} conflicts with stored data",
                )
            existing_materials += 1

        for expected_revision in expected_material.revisions:
            existing_revision = await session.get(
                MaterialRevision,
                expected_revision.id,
            )
            if existing_revision is not None:
                if not _revision_matches(
                    existing_revision,
                    expected_revision,
                    expected_material.id,
                ):
                    raise ManifestConflictError(
                        f"revision {expected_revision.id} conflicts with stored data",
                    )
                existing_revisions += 1
                continue

            revision_with_number = await session.scalar(
                select(MaterialRevision.id).where(
                    MaterialRevision.material_id == expected_material.id,
                    MaterialRevision.revision_number
                    == expected_revision.revision_number,
                ),
            )
            if revision_with_number is not None:
                raise ManifestConflictError(
                    "revision number "
                    f"{expected_revision.revision_number} for material "
                    f"{expected_material.id} already belongs to "
                    f"{revision_with_number}",
                )

            session.add(
                MaterialRevision(
                    id=expected_revision.id,
                    material_id=expected_material.id,
                    revision_number=expected_revision.revision_number,
                    status=expected_revision.status,
                    content=expected_revision.content,
                    url=expected_revision.url,
                ),
            )
            created_revisions += 1

    await session.flush()
    return ImportResult(
        created_materials=created_materials,
        existing_materials=existing_materials,
        created_revisions=created_revisions,
        existing_revisions=existing_revisions,
    )


async def execute_import(
    manifest: PlaceMaterialsManifest,
    *,
    dry_run: bool,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> ImportResult:
    """Import and commit, or always roll back in dry-run mode."""
    factory = session_factory or get_session_factory()
    async with factory() as session:
        try:
            result = await import_place_materials(session, manifest)
        except BaseException:
            await session.rollback()
            raise

        if dry_run:
            await session.rollback()
        else:
            await session.commit()
        return result


def load_manifest(filename: str) -> PlaceMaterialsManifest:
    """Load a UTF-8 JSON manifest from a file or standard input."""
    raw = sys.stdin.read() if filename == "-" else Path(filename).read_text("utf-8")
    return PlaceMaterialsManifest.model_validate_json(raw)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser without accessing external state."""
    parser = argparse.ArgumentParser(
        description="Import versioned place materials from a reviewed JSON manifest.",
    )
    parser.add_argument(
        "--file",
        required=True,
        help="UTF-8 JSON manifest path, or - to read standard input.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and query the database, then roll back every change.",
    )
    return parser


async def async_main(argv: Sequence[str] | None = None) -> int:
    """Run the importer and return a process exit code."""
    arguments = build_parser().parse_args(argv)
    try:
        manifest = load_manifest(arguments.file)
        result = await execute_import(manifest, dry_run=arguments.dry_run)
    except (OSError, ValueError, MaterialImportError) as error:
        print(f"Import failed: {error}", file=sys.stderr)
        return 1
    finally:
        await get_engine().dispose()

    mode = "Dry run" if arguments.dry_run else "Import"
    print(
        f"{mode} successful: "
        f"materials created={result.created_materials}, "
        f"already existed={result.existing_materials}; "
        f"revisions created={result.created_revisions}, "
        f"already existed={result.existing_revisions}.",
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Synchronous console entry point."""
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
