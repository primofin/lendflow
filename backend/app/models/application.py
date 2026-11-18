"""Loan application (docs/06 APPLICATIONS). LF-004 adds purpose and submission fields."""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ApplicationStatus(enum.StrEnum):
    """Subset of the docs/03 state machine; later stories add the other states."""

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"


class Application(Base):
    __tablename__ = "applications"

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
    assigned_officer: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    assigned_supervisor: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    submitted_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
