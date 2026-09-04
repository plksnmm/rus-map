import argparse
import asyncio
import math
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID

from geoalchemy2.elements import WKTElement
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import Float, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rus_map.db.session import get_engine, get_session_factory
from rus_map.models import Place
from rus_map.schemas.place import Latitude, Longitude, PlaceDescription, PlaceTitle

COORDINATE_ABS_TOLERANCE = 1e-7


class PlaceManifestItem(BaseModel):
    """One place with a stable identifier and validated coordinates."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    title: PlaceTitle
    description: PlaceDescription | None = None
    latitude: Latitude
    longitude: Longitude


class PlacesManifest(BaseModel):
    """Versioned JSON document accepted by the place importer."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    places: list[PlaceManifestItem] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "PlacesManifest":
        """Reject duplicate stable IDs before accessing the database."""
        place_ids = [place.id for place in self.places]
        if len(place_ids) != len(set(place_ids)):
            raise ValueError("place IDs must be unique")
        return self


@dataclass(frozen=True, slots=True)
class StoredPlace:
    """Existing database values used for conflict detection."""

    id: UUID
    title: str
    description: str | None
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class ImportResult:
    """Counts produced by an idempotent place import."""

    created_places: int = 0
    existing_places: int = 0


class PlaceImportError(Exception):
    """Base class for expected administrative place import failures."""


class ManifestConflictError(PlaceImportError):
    """A stable place UUID belongs to different stored data."""


async def _get_stored_place(
    session: AsyncSession,
    place_id: UUID,
) -> StoredPlace | None:
    statement = select(
        Place.id,
        Place.title,
        Place.description,
        func.ST_Y(Place.location, type_=Float).label("latitude"),
        func.ST_X(Place.location, type_=Float).label("longitude"),
    ).where(Place.id == place_id)
    row = (await session.execute(statement)).tuples().one_or_none()
    if row is None:
        return None
    return StoredPlace(
        id=row[0],
        title=row[1],
        description=row[2],
        latitude=row[3],
        longitude=row[4],
    )


def _place_matches(existing: StoredPlace, expected: PlaceManifestItem) -> bool:
    return (
        existing.id == expected.id
        and existing.title == expected.title
        and existing.description == expected.description
        and math.isclose(
            existing.latitude,
            expected.latitude,
            rel_tol=0,
            abs_tol=COORDINATE_ABS_TOLERANCE,
        )
        and math.isclose(
            existing.longitude,
            expected.longitude,
            rel_tol=0,
            abs_tol=COORDINATE_ABS_TOLERANCE,
        )
    )


async def import_places(
    session: AsyncSession,
    manifest: PlacesManifest,
) -> ImportResult:
    """Stage one idempotent place manifest in the caller's transaction."""
    created_places = 0
    existing_places = 0

    for expected_place in manifest.places:
        existing_place = await _get_stored_place(session, expected_place.id)
        if existing_place is not None:
            if not _place_matches(existing_place, expected_place):
                raise ManifestConflictError(
                    f"place {expected_place.id} conflicts with stored data",
                )
            existing_places += 1
            continue

        session.add(
            Place(
                id=expected_place.id,
                title=expected_place.title,
                description=expected_place.description,
                location=WKTElement(
                    f"POINT({expected_place.longitude} {expected_place.latitude})",
                    srid=4326,
                ),
            ),
        )
        created_places += 1

    await session.flush()
    return ImportResult(
        created_places=created_places,
        existing_places=existing_places,
    )


async def execute_import(
    manifest: PlacesManifest,
    *,
    dry_run: bool,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> ImportResult:
    """Import and commit, or always roll back in dry-run mode."""
    factory = session_factory or get_session_factory()
    async with factory() as session:
        try:
            result = await import_places(session, manifest)
        except BaseException:
            await session.rollback()
            raise

        if dry_run:
            await session.rollback()
        else:
            await session.commit()
        return result


def load_manifest(filename: str) -> PlacesManifest:
    """Load a UTF-8 JSON manifest from a file or standard input."""
    raw = sys.stdin.read() if filename == "-" else Path(filename).read_text("utf-8")
    return PlacesManifest.model_validate_json(raw)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser without accessing external state."""
    parser = argparse.ArgumentParser(
        description="Import places from a reviewed JSON manifest.",
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
    """Run the place importer and return a process exit code."""
    arguments = build_parser().parse_args(argv)
    try:
        manifest = load_manifest(arguments.file)
        result = await execute_import(manifest, dry_run=arguments.dry_run)
    except (OSError, ValueError, PlaceImportError) as error:
        print(f"Import failed: {error}", file=sys.stderr)
        return 1
    finally:
        await get_engine().dispose()

    mode = "Dry run" if arguments.dry_run else "Import"
    print(
        f"{mode} successful: "
        f"places created={result.created_places}, "
        f"already existed={result.existing_places}.",
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Synchronous console entry point."""
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
