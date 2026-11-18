"""Borrower profile (docs/06 BORROWER_PROFILES). Personal data: never log these fields."""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IncomeType(enum.StrEnum):
    """Income types from docs/02 section 3."""

    SALARIED = "salaried"
    FREELANCE = "freelance"
    SELF_EMPLOYED = "self_employed"
    RENTAL = "rental"
    OTHER = "other"


class BorrowerProfile(Base):
    __tablename__ = "borrower_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    full_name: Mapped[str | None] = mapped_column(String(200))
    date_of_birth: Mapped[date | None]
    national_id: Mapped[str | None] = mapped_column(String(12))  # 12 digits, synthetic
    address: Mapped[str | None] = mapped_column(String(500))
    income_type: Mapped[str | None] = mapped_column(String(20))
    monthly_income_vnd: Mapped[Decimal | None] = mapped_column(Numeric(18, 0))
    existing_debt_payment_vnd: Mapped[Decimal | None] = mapped_column(Numeric(18, 0))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
