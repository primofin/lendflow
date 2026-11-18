"""LF-008: the mock credit-bureau check as officers see it."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

CicStatus = Literal["running", "done", "timeout"]
CicFlag = Literal["pass", "attention", "recommend_reject"]  # BR-08; never an automatic rejection


class CicCheckOut(BaseModel):
    status: CicStatus
    progress_pct: int
    seconds_remaining: int | None
    attempt: int
    max_attempts: int
    message: str
    debt_group: int | None
    flag: CicFlag | None
    summary: str | None
    started_at: datetime
    finished_at: datetime | None
