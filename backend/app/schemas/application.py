"""Application schemas. LF-002 read model; LF-004 adds the submission payload."""

import uuid
from datetime import date, datetime
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.core.config import get_settings
from app.models.borrower_profile import IncomeType

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

    @field_validator("amount_vnd")
    @classmethod
    def _amount_in_range(cls, value: int) -> int:
        settings = get_settings()
        low, high = settings.amount_min_vnd, settings.amount_max_vnd
        if not low <= value <= high:
            raise ValueError(f"Amount must be between {low:,} and {high:,} VND")
        return value

    @field_validator("term_months")
    @classmethod
    def _term_allowed(cls, value: int) -> int:
        allowed = get_settings().allowed_terms_months
        if value not in allowed:
            raise ValueError(f"Term must be one of {', '.join(map(str, allowed))} months")
        return value

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
    purpose: str | None
    submitted_at: datetime | None
    created_at: datetime
