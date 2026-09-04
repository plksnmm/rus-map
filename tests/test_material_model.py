from sqlalchemy import Enum

from rus_map.models import Material, MaterialRevision


def test_material_table_has_lifecycle_constraints() -> None:
    table = Material.__table__

    assert table.schema == "app"
    place_foreign_key = next(iter(table.c.place_id.foreign_keys))

    assert place_foreign_key.target_fullname == "app.places.id"
    assert isinstance(table.c.type.type, Enum)
    assert table.c.type.type.enums == [
        "text",
        "external_link",
        "image",
        "video",
        "audio",
    ]
    assert table.c.status.type.enums == [
        "pending_review",
        "published",
        "rejected",
        "archived",
    ]
    assert {index.name for index in table.indexes} == {
        "idx_materials_place_status",
    }
    constraint_names = {constraint.name for constraint in table.constraints}
    assert "ck_materials_type" in constraint_names
    assert "ck_materials_status" in constraint_names


def test_revision_table_preserves_numbered_history() -> None:
    table = MaterialRevision.__table__
    constraint_names = {constraint.name for constraint in table.constraints}

    assert table.schema == "app"
    material_foreign_key = next(iter(table.c.material_id.foreign_keys))

    assert material_foreign_key.target_fullname == "app.materials.id"
    assert "uq_material_revisions_material_number" in constraint_names
    assert "ck_material_revisions_number_positive" in constraint_names
    assert "ck_material_revisions_exactly_one_value" in constraint_names
    assert "ck_material_revisions_content_not_blank" in constraint_names
    assert "ck_material_revisions_http_url" in constraint_names
    assert "ck_material_revisions_status" in constraint_names
    assert {index.name for index in table.indexes} == {
        "idx_material_revisions_material_status_number",
    }
