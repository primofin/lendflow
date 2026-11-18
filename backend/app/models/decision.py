"""Decisions and reason codes (BR-12 to BR-15, LF-011). See docs/06-data-model.md DECISIONS.

A decision is never edited. A correction is a new row whose `supersedes_id` points at the one it
replaces (BR-14). Like the audit log, immutability is enforced by database triggers (migration
0009), by the ORM guards below, and by having no route that changes a row.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Identity, String, Text, event
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapped, Mapper, mapped_column

from app.models.base import Base


class DecisionImmutable(Exception):
    """Raised when code tries to change or delete a decision."""


class ReasonCode(Base):
    """Rejection reasons, as data so Compliance can change the list (open item Q6)."""

    __tablename__ = "reason_codes"

    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    label: Mapped[str] = mapped_column(String(150))
    sort_order: Mapped[int]
    active: Mapped[bool] = mapped_column(default=True)


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Insertion order, assigned by the database: "the latest decision" never depends on clocks.
    seq: Mapped[int] = mapped_column(BigInteger, Identity(always=True), unique=True, index=True)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), index=True)
    decided_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    outcome: Mapped[str] = mapped_column(String(20))  # approve | reject | request_info | refer
    reason_code: Mapped[str | None] = mapped_column(ForeignKey("reason_codes.code"))
    explanation: Mapped[str | None] = mapped_column(Text)
    # BR-13: the documents or conditions that could change a rejection.
    conditions: Mapped[str | None] = mapped_column(Text)
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("decisions.id"))
    decided_at: Mapped[datetime]


@event.listens_for(Decision, "before_update")
def _refuse_update(mapper: Mapper[Any], connection: Connection, target: Decision) -> None:
    raise DecisionImmutable("Decisions are append-only; record a correction instead")


@event.listens_for(Decision, "before_delete")
def _refuse_delete(mapper: Mapper[Any], connection: Connection, target: Decision) -> None:
    raise DecisionImmutable("Decisions are append-only and cannot be deleted")
