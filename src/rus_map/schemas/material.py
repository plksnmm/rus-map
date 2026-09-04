from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, model_validator

from rus_map.models import MaterialType

MaterialTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
]
MaterialSource = Annotated[str, Field(max_length=500)]
MaterialContent = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
MaterialUrl = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^https?://", max_length=2048),
]


class MaterialRevisionResponse(BaseModel):
    """Latest public revision of a material."""

    revision_number: int = Field(gt=0)
    content: MaterialContent | None
    url: MaterialUrl | None
    media_id: UUID | None = None
    created_at: datetime

    @model_validator(mode="after")
    def exactly_one_value(self) -> "MaterialRevisionResponse":
        """Require either text content or a URL, but never both."""
        if (self.content is None) == (self.url is None):
            raise ValueError("revision must contain exactly one of content or url")
        return self


class MaterialResponse(BaseModel):
    """Published material returned for a place."""

    id: UUID
    type: MaterialType
    title: MaterialTitle
    source: MaterialSource | None
    revision: MaterialRevisionResponse
    created_at: datetime
    updated_at: datetime


class MaterialListResponse(BaseModel):
    """Published materials linked to a place."""

    items: list[MaterialResponse]
    total: int = Field(ge=0)
