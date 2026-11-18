"""LF-019 operations dashboard: numbers only, no applicant data."""

from datetime import date

from pydantic import BaseModel, Field, model_validator


class DashboardParams(BaseModel):
    date_from: date | None = Field(default=None, alias="from")
    date_to: date | None = Field(default=None, alias="to")

    @model_validator(mode="after")
    def _ordered(self) -> "DashboardParams":
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("The start date must not be after the end date")
        return self


class StatusCount(BaseModel):
    status: str
    count: int


class DashboardOut(BaseModel):
    date_from: date
    date_to: date  # inclusive
    total_applications: int
    by_status: list[StatusCount]  # applications created in the range, workflow order, zeros kept
    decided: int  # applications whose first approve/reject decision fell in the range
    approved: int
    rejected: int
    approval_rate_percent: float | None
    avg_decision_hours: float | None  # submission to the first approve/reject decision
    overdue_now: int  # supervisor SLA breaches still open (a snapshot, not range-bound)
