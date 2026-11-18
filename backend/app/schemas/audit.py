"""LF-016 audit log search and entries. Entries hold ids and actions, never request bodies."""

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.user import Role


class AuditSearchParams(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    application_id: uuid.UUID | None = None
    actor_id: uuid.UUID | None = None
    action: str | None = Field(default=None, max_length=64)
    created_from: datetime | None = Field(default=None, alias="from")
    created_to: datetime | None = Field(default=None, alias="to")
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)

    @field_validator("created_from", "created_to")
    @classmethod
    def _assume_utc(cls, value: datetime | None) -> datetime | None:
        return value.replace(tzinfo=UTC) if value is not None and value.tzinfo is None else value


class AuditEntryOut(BaseModel):
    seq: int
    id: uuid.UUID
    created_at: datetime
    actor_id: uuid.UUID | None
    actor_email: str | None
    actor_role: Role | None
    action: str
    target_type: str | None
    target_id: uuid.UUID | None
    application_id: uuid.UUID | None
    ip_address: str | None
