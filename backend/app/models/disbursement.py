"""Disbursement and simulated face match (LF-020, C-07). See docs/06-data-model.md.

A disbursement is never edited (database triggers, migration 0016, plus the ORM guards below).
A face-match attempt is single-use, so it carries a `consumed_at` that is set once.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Identity, Numeric, event
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapped, Mapper, mapped_column

from app.models.base import Base


class DisbursementImmutable(Exception):
    """Raised when code tries to change or delete a disbursement."""


class FaceMatch(Base):
    __tablename__ = "face_matches"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), index=True)
    performed_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    passed: Mapped[bool]
    created_at: Mapped[datetime]
    consumed_at: Mapped[datetime | None]


class Disbursement(Base):
    __tablename__ = "disbursements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    seq: Mapped[int] = mapped_column(BigInteger, Identity(always=True), unique=True, index=True)
    # One disbursement per application (unique): the loan is paid out once.
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), unique=True)
    amount_vnd: Mapped[int] = mapped_column(Numeric(18, 0))
    disbursed_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    face_match_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("face_matches.id"))
    disbursed_at: Mapped[datetime]


@event.listens_for(Disbursement, "before_update")
def _refuse_update(mapper: Mapper[Any], connection: Connection, target: Disbursement) -> None:
    raise DisbursementImmutable("Disbursements are append-only")


@event.listens_for(Disbursement, "before_delete")
def _refuse_delete(mapper: Mapper[Any], connection: Connection, target: Disbursement) -> None:
    raise DisbursementImmutable("Disbursements are append-only and cannot be deleted")
