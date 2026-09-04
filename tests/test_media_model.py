from rus_map.models import MaterialRevision, MediaAsset


def test_media_asset_table_has_storage_constraints() -> None:
    table = MediaAsset.__table__
    assert table.schema == "app"
    assert table.c.sha256.unique
    assert table.c.original_storage_key.unique
    assert table.c.display_storage_key.unique
    names = {constraint.name for constraint in table.constraints}
    assert "ck_media_assets_original_size" in names
    assert "ck_media_assets_display_size" in names
    assert "ck_media_assets_dimensions" in names


def test_material_revision_can_reference_media_asset() -> None:
    foreign_key = next(iter(MaterialRevision.__table__.c.media_asset_id.foreign_keys))
    assert foreign_key.target_fullname == "app.media_assets.id"
