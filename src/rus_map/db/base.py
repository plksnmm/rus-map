from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy database models."""

    metadata = MetaData(schema="app")
