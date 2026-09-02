from geoalchemy2 import Geometry
from sqlalchemy import DateTime, String, Text

from rus_map.models.place import Place


def test_place_table_structure() -> None:
    """Place maps the required fields to the application schema."""
    table = Place.__table__

    assert table.name == "places"
    assert table.schema == "app"
    assert set(table.columns.keys()) == {
        "id",
        "title",
        "description",
        "location",
        "created_at",
        "updated_at",
    }
    assert table.c.id.primary_key
    assert not table.c.title.nullable
    assert isinstance(table.c.title.type, String)
    assert table.c.title.type.length == 200
    assert table.c.description.nullable
    assert isinstance(table.c.description.type, Text)
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone
    assert isinstance(table.c.updated_at.type, DateTime)
    assert table.c.updated_at.type.timezone


def test_place_location_is_indexed_postgis_point() -> None:
    """A place location uses WGS 84 and has a spatial index."""
    table = Place.__table__
    location_type = table.c.location.type

    assert isinstance(location_type, Geometry)
    assert location_type.geometry_type == "POINT"
    assert location_type.srid == 4326
    assert not table.c.location.nullable

    location_index = next(
        index for index in table.indexes if index.name == "idx_places_location"
    )
    assert location_index.dialect_options["postgresql"]["using"] == "gist"
