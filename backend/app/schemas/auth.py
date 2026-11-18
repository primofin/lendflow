"""Request/response schemas for LF-001 authentication."""

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.config import get_settings
from app.models.user import Role


def check_password_policy(value: str) -> str:
    """LF-001 password policy, shared by self-registration and staff-created accounts."""
    minimum = get_settings().password_min_length
    if len(value) < minimum:
        raise ValueError(f"Password must be at least {minimum} characters")
    return value


class RegisterIn(BaseModel):
    # Extra fields such as "role" are ignored: self-registration is always a borrower.
    email: EmailStr
    password: str = Field(max_length=256)

    _password_policy = field_validator("password")(check_password_policy)


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
