"""LF-002 user-management schemas (supervisor only)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import Role
from app.schemas.auth import check_password_policy


class UserCreateIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=256)
    role: Role

    _password_policy = field_validator("password")(check_password_policy)


class RoleChangeIn(BaseModel):
    role: Role


class UserAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: Role
    is_active: bool
    created_at: datetime
