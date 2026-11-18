"""Append-only audit trail (BR-14, LF-016). See docs/06-data-model.md AUDIT_LOGS.

Immutability is enforced in three places: database triggers (migration 0006) that reject
UPDATE, DELETE and TRUNCATE for every connection; the ORM guard below, which fails fast with a
clear error; and the absence of any write route. Only audit_service.record() inserts rows.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Identity, String, event
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapped, Mapper, mapped_column

from app.models.base import Base


class AuditLogImmutable(Exception):
    """Raised when code tries to change or delete an audit entry."""


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Insertion order, assigned by the database. Orders and pages the log exactly, even when
    # many entries share a timestamp.
    seq: Mapped[int] = mapped_column(BigInteger, Identity(always=True), unique=True, index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(64))
    target_type: Mapped[str | None] = mapped_column(String(64))
    target_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    # The application this entry belongs to (directly, or through one of its documents), so the
    # full history of an application is one indexed lookup.
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("applications.id"), index=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime]


@event.listens_for(AuditLog, "before_update")
def _refuse_update(mapper: Mapper[Any], connection: Connection, target: AuditLog) -> None:
    raise AuditLogImmutable("Audit entries are append-only and cannot be modified")


@event.listens_for(AuditLog, "before_delete")
def _refuse_delete(mapper: Mapper[Any], connection: Connection, target: AuditLog) -> None:
    raise AuditLogImmutable("Audit entries are append-only and cannot be deleted")
