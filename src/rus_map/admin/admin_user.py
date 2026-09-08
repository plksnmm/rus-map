import argparse
import asyncio
import getpass
import sys

from sqlalchemy.exc import IntegrityError

from rus_map.db.session import get_engine, get_session_factory
from rus_map.repositories.auth import AdminAuthRepository
from rus_map.services.auth import hash_password, normalize_username


def validate_username(value: str) -> str:
    username = normalize_username(value)
    if not 3 <= len(username) <= 64:
        raise ValueError("username must contain between 3 and 64 characters")
    if not all(character.isalnum() or character in "._-" for character in username):
        raise ValueError(
            "username may contain letters, numbers, dots, dashes and underscores"
        )
    return username


def read_password() -> str:
    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Repeat password: ")
    if password != confirmation:
        raise ValueError("passwords do not match")
    if not 12 <= len(password) <= 1024:
        raise ValueError("password must contain between 12 and 1024 characters")
    return password


async def create_admin(username: str, password: str) -> None:
    engine = get_engine()
    try:
        factory = get_session_factory()
        async with factory() as session:
            repository = AdminAuthRepository(session)
            try:
                await repository.create_admin(username, hash_password(password))
                await session.commit()
            except IntegrityError as error:
                await session.rollback()
                raise ValueError("administrator already exists") from error
    finally:
        await engine.dispose()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage Rus Map administrator accounts without exposing passwords."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    create_parser = subparsers.add_parser("create", help="Create an administrator")
    create_parser.add_argument("--username", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        if args.command == "create":
            username = validate_username(args.username)
            password = read_password()
            asyncio.run(create_admin(username, password))
            print(f"Administrator '{username}' created.")
    except (ValueError, EOFError, KeyboardInterrupt) as error:
        print(f"Administrator creation failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
