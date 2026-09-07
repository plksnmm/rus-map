import hashlib
from pathlib import Path
from uuid import UUID

from PIL import Image

from rus_map.admin.image_import import load_manifest as load_images_manifest
from rus_map.admin.material_import import load_manifest
from rus_map.models import ModerationStatus

MANIFEST_PATH = Path("content/places/sysert-electrotechnical-plant.json")
IMAGES_MANIFEST_PATH = Path("content/places/sysert-electrotechnical-plant-images.json")
MEDIA_ROOT = Path("content/media")
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


def test_sysert_image_manifest_matches_publication() -> None:
    manifest = load_images_manifest(str(IMAGES_MANIFEST_PATH))
    image = manifest.images[0]

    assert manifest.schema_version == 1
    assert manifest.place_id == SYSERT_PLACE_ID
    assert len(manifest.images) == 1
    assert image.status is ModerationStatus.PUBLISHED
    assert image.title == "Иллюстрация к публикации «Сысертский завод»"
    assert image.source == "Русь пролетарская"
    assert image.source_url == "https://t.me/rus_proletarskaya/306"


def test_sysert_image_file_matches_manifest_hash() -> None:
    manifest = load_images_manifest(str(IMAGES_MANIFEST_PATH))
    image = manifest.images[0]
    image_path = MEDIA_ROOT / image.file
    image_bytes = image_path.read_bytes()

    assert hashlib.sha256(image_bytes).hexdigest() == image.sha256
    with Image.open(image_path) as opened:
        assert opened.size == (800, 450)
        opened.verify()


def test_sysert_image_ids_do_not_reuse_material_ids() -> None:
    materials_manifest = load_manifest(str(MANIFEST_PATH))
    images_manifest = load_images_manifest(str(IMAGES_MANIFEST_PATH))
    existing_ids = {material.id for material in materials_manifest.materials}
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
