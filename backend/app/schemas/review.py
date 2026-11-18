"""F4: what staff see when they open a file. The national ID is masked to its last four digits."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

Flag = Literal["exception", "high_dti", "fast_track", "overdue"]


class ApplicantOut(BaseModel):
    full_name: str | None
    date_of_birth: date | None
    national_id_masked: str | None
    address: str | None
    income_type: str | None
    monthly_income_vnd: int | None
    existing_debt_payment_vnd: int | None


class ReviewOut(BaseModel):
    id: uuid.UUID
    status: str
    amount_vnd: int
    term_months: int
    purpose: str | None
    annual_rate_percent: float | None
    submitted_at: datetime | None
    flags: list[Flag]
    assigned_to_me: bool
    assigned: bool  # whether an officer has the file; identities are not exposed
    supervisor_assigned: bool
    applicant: ApplicantOut
