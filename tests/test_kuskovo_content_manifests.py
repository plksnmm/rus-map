from pathlib import Path
from uuid import UUID

from rus_map.admin.material_import import load_manifest as load_materials_manifest
from rus_map.admin.place_import import load_manifest as load_places_manifest
from rus_map.models import ModerationStatus

PLACE_MANIFEST_PATH = Path("content/places/kuskovo-chemical-plant-place.json")
MATERIALS_MANIFEST_PATH = Path("content/places/kuskovo-chemical-plant-materials.json")
KUSKOVO_PLACE_ID = UUID("bbe880f1-4bf5-4b49-889a-7ccab143a6dd")


def test_kuskovo_place_manifest_is_valid() -> None:
    manifest = load_places_manifest(str(PLACE_MANIFEST_PATH))
    place = manifest.places[0]

    assert manifest.schema_version == 1
    assert len(manifest.places) == 1
    assert place.id == KUSKOVO_PLACE_ID
    assert place.title == "Кусковский ордена «Знак Почёта» химический завод"
    assert place.latitude == 55.7433
    assert place.longitude == 37.803
    assert "снесённое" in (place.description or "")


def test_kuskovo_materials_manifest_is_valid_and_published() -> None:
    manifest = load_materials_manifest(str(MATERIALS_MANIFEST_PATH))

    assert manifest.schema_version == 1
    assert manifest.place_id == KUSKOVO_PLACE_ID
    assert len(manifest.materials) == 6
    assert all(
        material.status is ModerationStatus.PUBLISHED for material in manifest.materials
    )
    assert all(
        revision.status is ModerationStatus.PUBLISHED
        for material in manifest.materials
        for revision in material.revisions
    )


def test_kuskovo_manifests_use_unique_stable_ids() -> None:
    place_manifest = load_places_manifest(str(PLACE_MANIFEST_PATH))
    materials_manifest = load_materials_manifest(str(MATERIALS_MANIFEST_PATH))
    place_ids = {place.id for place in place_manifest.places}
    material_ids = {material.id for material in materials_manifest.materials}
    revision_ids = {
        revision.id
        for material in materials_manifest.materials
        for revision in material.revisions
    }

    assert len(material_ids) == len(materials_manifest.materials)
    assert len(revision_ids) == sum(
        len(material.revisions) for material in materials_manifest.materials
    )
    assert place_ids.isdisjoint(material_ids)
    assert place_ids.isdisjoint(revision_ids)
    assert material_ids.isdisjoint(revision_ids)


def test_kuskovo_manifest_preserves_every_reviewed_source() -> None:
    manifest = load_materials_manifest(str(MATERIALS_MANIFEST_PATH))
    urls = {
        revision.url
        for material in manifest.materials
        for revision in material.revisions
        if revision.url is not None
    }

    assert urls == {
        "https://t.me/rus_proletarskaya/266",
        "https://goskatalog.ru/portal/#/collections?id=16565850",
        "https://goskatalog.ru/portal/#/collections?id=16566382",
        "https://goskatalog.ru/portal/#/collections?id=16565672",
        "https://goskatalog.ru/portal/#/collections?id=16565419",
    }
