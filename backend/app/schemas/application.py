"""Application read schema. Minimal for LF-002; extended in LF-004."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    amount_vnd: int  # whole VND
    term_months: int
    created_at: datetime
