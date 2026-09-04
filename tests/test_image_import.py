import hashlib
import io
from pathlib import Path
from uuid import uuid4

import pytest
from PIL import Image
from pydantic import ValidationError

from rus_map.admin.image_import import (
    ImageImportError,
    ImageManifestItem,
    PlaceImagesManifest,
    prepare_image,
)


def make_png(path: Path, size: tuple[int, int] = (2400, 1200)) -> str:
    output = io.BytesIO()
    Image.new("RGB", size, "#a82626").save(output, format="PNG")
    data = output.getvalue()
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def item(filename: str, digest: str) -> ImageManifestItem:
    return ImageManifestItem(
        media_id=uuid4(),
        material_id=uuid4(),
        revision_id=uuid4(),
        status="published",
        title="Кусковский химический завод, 1964 год",
        source="Государственный каталог",
        source_url="https://t.me/rus_proletarskaya/266",
        file=filename,
        sha256=digest,
    )


def test_prepare_image_verifies_and_optimizes_source(tmp_path: Path) -> None:
    digest = make_png(tmp_path / "factory.png")
    prepared = prepare_image(item("factory.png", digest), tmp_path)

    assert prepared.original_content_type == "image/png"
    assert prepared.width == 1920
    assert prepared.height == 960
    assert prepared.display_storage_key.endswith(".webp")
    with Image.open(io.BytesIO(prepared.display_bytes)) as display:
        assert display.format == "WEBP"


def test_prepare_image_rejects_wrong_hash(tmp_path: Path) -> None:
    make_png(tmp_path / "factory.png", (20, 20))
    with pytest.raises(ImageImportError, match="SHA-256 mismatch"):
        prepare_image(item("factory.png", "0" * 64), tmp_path)


def test_manifest_rejects_path_traversal() -> None:
    with pytest.raises(ValidationError, match="safe relative path"):
        item("../secret.png", "0" * 64)


def test_manifest_rejects_duplicate_ids() -> None:
    first = item("one.png", "0" * 64)
    second = item("two.png", "1" * 64).model_copy(update={"media_id": first.media_id})
    with pytest.raises(ValidationError, match="media_id values must be unique"):
        PlaceImagesManifest(schema_version=1, place_id=uuid4(), images=[first, second])
