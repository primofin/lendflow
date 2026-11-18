"""Request/response schemas for LF-001 authentication."""

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.config import get_settings
from app.models.user import Role


class RegisterIn(BaseModel):
    # Extra fields such as "role" are ignored: self-registration is always a borrower.
    email: EmailStr
    password: str = Field(max_length=256)

    @field_validator("password")
    @classmethod
    def _password_policy(cls, value: str) -> str:
        minimum = get_settings().password_min_length
        if len(value) < minimum:
            raise ValueError(f"Password must be at least {minimum} characters")
        return value


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=256)


class RefreshIn(BaseModel):
    refresh_token: str = Field(max_length=512)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105  (OAuth token type, not a secret)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: Role
