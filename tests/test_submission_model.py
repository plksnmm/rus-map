from sqlalchemy.dialects import postgresql

from rus_map.models import PlaceSubmission, SubmissionStatus


def test_submission_model_has_moderation_constraints_and_index() -> None:
    table = PlaceSubmission.__table__
    constraints = {constraint.name for constraint in table.constraints}
    indexes = {index.name for index in table.indexes}

    assert table.schema == "app"
    assert {
        "ck_place_submissions_status",
        "ck_place_submissions_title_not_blank",
        "ck_place_submissions_latitude",
        "ck_place_submissions_longitude",
        "ck_place_submissions_moderation_result",
    }.issubset(constraints)
    assert "idx_place_submissions_status_created" in indexes
    assert table.c.approved_place_id.unique is True
    assert (
        next(iter(table.c.approved_place_id.foreign_keys)).target_fullname
        == "app.places.id"
    )


def test_submission_defaults_to_pending_and_uses_jsonb_sources() -> None:
    table = PlaceSubmission.__table__

    assert table.c.status.server_default is not None
    assert table.c.status.server_default.arg == SubmissionStatus.PENDING.value
    assert table.c.source_urls.server_default is not None
    assert table.c.source_urls.type.compile(dialect=postgresql.dialect()) == "JSONB"
