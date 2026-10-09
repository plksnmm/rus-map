from pathlib import Path
from uuid import UUID

from rus_map.admin.material_import import load_manifest as load_materials_manifest
from rus_map.admin.place_import import load_manifest as load_places_manifest
from rus_map.models import ModerationStatus

PLACES_MANIFEST_PATH = Path("content/places/yaroslavl-red-perekop-places.json")
MATERIALS_MANIFEST_PATHS = (
    Path("content/places/yaroslavl-peter-and-paul-church-materials.json"),
    Path("content/places/yaroslavl-workers-memorial-materials.json"),
    Path("content/places/yaroslavl-big-manufactory-materials.json"),
)
PLACE_IDS = {
    UUID("531c004b-e7d4-40a4-9605-13481401931a"),
    UUID("1ee1a2eb-b60f-4b31-bc7d-81afe5664724"),
    UUID("38ed1b06-8e68-4ca1-96d5-2c47baf66d78"),
}


def test_yaroslavl_places_manifest_is_valid() -> None:
    manifest = load_places_manifest(str(PLACES_MANIFEST_PATH))

    assert manifest.schema_version == 1
    assert {place.id for place in manifest.places} == PLACE_IDS
    assert len(manifest.places) == 3
    assert all(
        "рабоч" in (place.description or "").lower() for place in manifest.places
    )


def test_yaroslavl_materials_are_valid_and_published() -> None:
    manifests = [
        load_materials_manifest(str(path)) for path in MATERIALS_MANIFEST_PATHS
    ]

    assert {manifest.place_id for manifest in manifests} == PLACE_IDS
    assert all(
        material.status is ModerationStatus.PUBLISHED
        for manifest in manifests
        for material in manifest.materials
    )
    assert all(
        revision.status is ModerationStatus.PUBLISHED
        for manifest in manifests
        for material in manifest.materials
        for revision in material.revisions
    )


def test_yaroslavl_manifests_use_unique_stable_ids() -> None:
    place_manifest = load_places_manifest(str(PLACES_MANIFEST_PATH))
    material_manifests = [
        load_materials_manifest(str(path)) for path in MATERIALS_MANIFEST_PATHS
    ]
    place_ids = {place.id for place in place_manifest.places}
    material_ids = {
        material.id
        for manifest in material_manifests
        for material in manifest.materials
    }
    revision_ids = {
        revision.id
        for manifest in material_manifests
        for material in manifest.materials
        for revision in material.revisions
    }
    material_count = sum(len(manifest.materials) for manifest in material_manifests)
    revision_count = sum(
        len(material.revisions)
        for manifest in material_manifests
        for material in manifest.materials
    )

    assert len(material_ids) == material_count
    assert len(revision_ids) == revision_count
    assert place_ids.isdisjoint(material_ids)
    assert place_ids.isdisjoint(revision_ids)
    assert material_ids.isdisjoint(revision_ids)


def test_yaroslavl_source_publication_and_video_are_preserved() -> None:
    manifests = [
        load_materials_manifest(str(path)) for path in MATERIALS_MANIFEST_PATHS
    ]
    urls = {
        revision.url
        for manifest in manifests
        for material in manifest.materials
        for revision in material.revisions
        if revision.url is not None
    }

    assert "https://t.me/rus_proletarskaya/114" in urls
    assert "https://youtu.be/R3Q6pv-eEm4" in urls
