import pytest

from rus_map.admin.admin_user import build_parser, validate_username


def test_admin_username_is_normalized() -> None:
    assert validate_username(" Editor.Name ") == "editor.name"


@pytest.mark.parametrize("username", ["ab", "bad name", "editor!"])
def test_admin_username_rejects_unsafe_values(username: str) -> None:
    with pytest.raises(ValueError):
        validate_username(username)


def test_cli_has_no_password_argument() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(
            ["create", "--username", "editor", "--password", "leaked"]
        )
