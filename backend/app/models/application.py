"""Loan application (docs/06 APPLICATIONS). Minimal for LF-002; LF-004 adds the remaining fields."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    borrower_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("borrower_profiles.id"), index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    amount_vnd: Mapped[Decimal] = mapped_column(Numeric(18, 0))  # whole VND, never float
    term_months: Mapped[int]
    status: Mapped[str] = mapped_column(String(30), default="draft")
    exception_flag: Mapped[bool] = mapped_column(default=False)
    assigned_officer: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
