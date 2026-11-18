"""Loan application (docs/06 APPLICATIONS). LF-004 adds purpose and submission fields."""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ApplicationStatus(enum.StrEnum):
    """Subset of the docs/03 state machine; later stories add the other states."""

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    IN_REVIEW = "IN_REVIEW"  # LF-010: mandatory documents in (or waived); queued for an officer
    # LF-011: set only by recording a decision (BR-15), never by a background job.
    NEEDS_INFO = "NEEDS_INFO"
    REFERRED = "REFERRED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (Index("ix_applications_status_submitted_at", "status", "submitted_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    borrower_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("borrower_profiles.id"), index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    amount_vnd: Mapped[Decimal] = mapped_column(Numeric(18, 0))  # whole VND, never float
    term_months: Mapped[int]
    annual_rate: Mapped[Decimal | None] = mapped_column(Numeric(7, 4))  # set by LF-003
    purpose: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default=ApplicationStatus.DRAFT.value)
    # Snapshot of the borrower's income type at submission: the profile is overwritten by later
    # applications, but this application's document requirements must not change (LF-007).
    income_type: Mapped[str | None] = mapped_column(String(20))
    exception_flag: Mapped[bool] = mapped_column(default=False)
    # LF-010 queue flags. Always false until LF-008 (CIC) and LF-009 (AI review) compute them.
    high_dti: Mapped[bool] = mapped_column(default=False)  # BR-07
    fast_track: Mapped[bool] = mapped_column(default=False)  # BR-09
    assigned_officer: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    assigned_supervisor: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    # LF-017 / BR-11: when the file started waiting at a supervisor, and when the SLA was missed.
    # LF-013: set when the application was created by a CSV import (always a DRAFT).
    import_job_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("import_jobs.id"))
    assigned_supervisor_at: Mapped[datetime | None]
    sla_breached_at: Mapped[datetime | None]
    submitted_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
