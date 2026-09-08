from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AdminLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("username")
    @classmethod
    def username_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("username must not be blank")
        return value


class AdminResponse(BaseModel):
    id: UUID
    username: str


class AdminLoginResponse(BaseModel):
    admin: AdminResponse
    expires_at: datetime
