import hashlib
from pathlib import Path
from uuid import UUID

from PIL import Image

from rus_map.admin.image_import import load_manifest as load_images_manifest
from rus_map.admin.material_import import load_manifest as load_materials_manifest
from rus_map.admin.place_import import load_manifest as load_places_manifest
from rus_map.models import ModerationStatus

PLACE_MANIFEST_PATH = Path("content/places/kuskovo-chemical-plant-place.json")
MATERIALS_MANIFEST_PATH = Path("content/places/kuskovo-chemical-plant-materials.json")
IMAGES_MANIFEST_PATH = Path("content/places/kuskovo-chemical-plant-images.json")
MEDIA_ROOT = Path("content/media")
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


def test_kuskovo_images_manifest_matches_reviewed_sources() -> None:
    manifest = load_images_manifest(str(IMAGES_MANIFEST_PATH))

    assert manifest.schema_version == 1
    assert manifest.place_id == KUSKOVO_PLACE_ID
    assert len(manifest.images) == 4
    assert all(image.status is ModerationStatus.PUBLISHED for image in manifest.images)
    assert {image.source_url for image in manifest.images} == {
        "https://goskatalog.ru/portal/#/collections?id=16565850",
        "https://goskatalog.ru/portal/#/collections?id=16566382",
        "https://goskatalog.ru/portal/#/collections?id=16565672",
        "https://goskatalog.ru/portal/#/collections?id=16565419",
    }


def test_kuskovo_image_files_match_manifest_hashes() -> None:
    manifest = load_images_manifest(str(IMAGES_MANIFEST_PATH))

    for image in manifest.images:
        image_path = MEDIA_ROOT / image.file
        image_bytes = image_path.read_bytes()
        assert hashlib.sha256(image_bytes).hexdigest() == image.sha256
        with Image.open(image_path) as opened:
            opened.verify()


def test_kuskovo_image_ids_do_not_reuse_existing_content_ids() -> None:
    place_manifest = load_places_manifest(str(PLACE_MANIFEST_PATH))
    materials_manifest = load_materials_manifest(str(MATERIALS_MANIFEST_PATH))
    images_manifest = load_images_manifest(str(IMAGES_MANIFEST_PATH))
    existing_ids = {place.id for place in place_manifest.places}
    existing_ids.update(material.id for material in materials_manifest.materials)
    existing_ids.update(
        revision.id
        for material in materials_manifest.materials
        for revision in material.revisions
    )
    image_ids = {
        identifier
        for image in images_manifest.images
        for identifier in (image.media_id, image.material_id, image.revision_id)
    }

    assert len(image_ids) == len(images_manifest.images) * 3
    assert existing_ids.isdisjoint(image_ids)
