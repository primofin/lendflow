"""LF-014 repayment schedule and reminder settings."""

import uuid
from datetime import date

from pydantic import BaseModel


class InstalmentOut(BaseModel):
    number: int
    due_date: date
    payment_vnd: int
    principal_vnd: int
    interest_vnd: int
    balance_vnd: int


class ScheduleOut(BaseModel):
    application_id: uuid.UUID
    start_date: date  # the approval date; the first instalment is due one month later
    annual_rate_percent: float
    term_months: int
    monthly_payment_vnd: int
    total_paid_vnd: int
    total_interest_vnd: int
    instalments: list[InstalmentOut]


class ReminderSettings(BaseModel):
    repayment_reminders: bool
