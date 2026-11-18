"""Application schemas. LF-002 read model; LF-004 adds the submission payload."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    computed_field,
    field_validator,
    model_validator,
)

from app.core.config import get_settings
from app.models.borrower_profile import IncomeType
from app.schemas.loan_terms import check_amount, check_term

NationalId = Annotated[str, StringConstraints(strip_whitespace=True)]


class ProfileIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    date_of_birth: date
    national_id: NationalId
    address: str = Field(min_length=1, max_length=500)
    income_type: IncomeType
    monthly_income_vnd: int = Field(ge=0)
    existing_debt_payment_vnd: int = Field(default=0, ge=0)

    @field_validator("national_id")
    @classmethod
    def _twelve_digits(cls, value: str) -> str:
        # BR-04. Legacy 9-digit IDs are rejected until Compliance answers open item Q2.
        if len(value) != 12 or not value.isascii() or not value.isdigit():
            raise ValueError("National ID must be 12 digits")
        return value


class ApplicationSubmitIn(BaseModel):
    amount_vnd: int
    term_months: int
    purpose: str | None = None
    profile: ProfileIn
    consent_accepted: bool
    consent_version: str = Field(max_length=32)

    _amount_in_range = field_validator("amount_vnd")(check_amount)
    _term_allowed = field_validator("term_months")(check_term)

    @model_validator(mode="after")
    def _purpose_and_consent(self) -> Self:
        if not self.consent_accepted:
            raise ValueError("You must accept the consent to submit an application")
        threshold = get_settings().purpose_required_from_vnd
        if self.amount_vnd >= threshold and not (self.purpose or "").strip():
            raise ValueError(f"A purpose is required for loans of {threshold:,} VND or more")
        return self


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    amount_vnd: int  # whole VND
    term_months: int
    annual_rate: Decimal | None = Field(default=None, exclude=True)
    purpose: str | None
    submitted_at: datetime | None
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def annual_rate_percent(self) -> float | None:
        """Display value only (e.g. 16.0); the exact rate is stored as a Decimal fraction."""
        return None if self.annual_rate is None else float(self.annual_rate * 100)
