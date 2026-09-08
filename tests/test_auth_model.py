from rus_map.models import AdminLoginThrottle, AdminSession, AdminUser


def test_admin_auth_models_use_application_schema_and_security_indexes() -> None:
    assert AdminUser.__table__.schema == "app"
    assert AdminSession.__table__.schema == "app"
    assert AdminLoginThrottle.__table__.schema == "app"
    assert AdminUser.__table__.c.username.unique is True
    assert AdminSession.__table__.c.token_hash.unique is True
    assert {
        "idx_admin_sessions_admin_expires",
        "idx_admin_sessions_expires",
    } == {index.name for index in AdminSession.__table__.indexes}
    assert "idx_admin_login_throttles_updated" in {
        index.name for index in AdminLoginThrottle.__table__.indexes
    }


def test_admin_session_references_admin_with_cascade_delete() -> None:
    foreign_key = next(iter(AdminSession.__table__.c.admin_id.foreign_keys))
    assert foreign_key.target_fullname == "app.admin_users.id"
    assert foreign_key.ondelete == "CASCADE"
