"""LF-010 officer queue: filters and rows. Rows carry the applicant's name and no documents."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

QueueStatus = Literal["IN_REVIEW", "SUBMITTED", "REFERRED"]
QueueFlag = Literal["exception", "high_dti", "fast_track", "overdue"]
QueueSort = Literal["oldest", "newest"]


class QueueParams(BaseModel):
    status: QueueStatus = "IN_REVIEW"
    flag: QueueFlag | None = None
    sort: QueueSort = "oldest"
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class QueueItemOut(BaseModel):
    id: uuid.UUID
    status: str
    applicant_name: str | None
    amount_vnd: int
    term_months: int
    flags: list[QueueFlag]
    submitted_at: datetime | None
    age_hours: float | None


class QueuePageOut(BaseModel):
    items: list[QueueItemOut]
    total: int
    limit: int
    offset: int
    message: str | None = None
