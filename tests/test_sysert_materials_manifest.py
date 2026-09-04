from pathlib import Path
from uuid import UUID

from rus_map.admin.material_import import load_manifest
from rus_map.models import ModerationStatus

MANIFEST_PATH = Path("content/places/sysert-electrotechnical-plant.json")
SYSERT_PLACE_ID = UUID("e2457cad-b0e2-45b4-8e76-81e09b3d1fed")


def test_sysert_manifest_is_valid_and_fully_published() -> None:
    manifest = load_manifest(str(MANIFEST_PATH))

    assert manifest.schema_version == 1
    assert manifest.place_id == SYSERT_PLACE_ID
    assert len(manifest.materials) == 4
    assert all(
        material.status is ModerationStatus.PUBLISHED for material in manifest.materials
    )
    assert all(
        revision.status is ModerationStatus.PUBLISHED
        for material in manifest.materials
        for revision in material.revisions
    )


def test_sysert_manifest_uses_unique_stable_ids() -> None:
    manifest = load_manifest(str(MANIFEST_PATH))
    material_ids = [material.id for material in manifest.materials]
    revision_ids = [
        revision.id
        for material in manifest.materials
        for revision in material.revisions
    ]

    assert len(material_ids) == len(set(material_ids))
    assert len(revision_ids) == len(set(revision_ids))
    assert set(material_ids).isdisjoint(revision_ids)


def test_sysert_manifest_contains_reviewed_sources() -> None:
    manifest = load_manifest(str(MANIFEST_PATH))
    urls = {
        revision.url
        for material in manifest.materials
        for revision in material.revisions
        if revision.url is not None
    }

    assert urls == {
        "https://t.me/rus_proletarskaya/306",
        "https://youtu.be/Dh-ZcOVh8zw",
        "https://dzen.ru/video/watch/68ea58c270153c7016fd1e21",
    }
