"""LF-012 borrower status tracker. Shows steps and what to do next; never who decided."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.decision import BorrowerDecisionOut

StepState = Literal["done", "current", "upcoming", "skipped"]


class TrackerStepOut(BaseModel):
    label: str
    state: StepState
    updated_at: datetime | None  # last update of this step; none if it has not been reached


class MissingItemOut(BaseModel):
    label: str
    accepted_types: list[str]  # any one of these satisfies the item


class NeedsInfoOut(BaseModel):
    message: str | None  # the officer's request, in their words
    missing_documents: list[MissingItemOut]
    upload_url: str  # existing upload endpoint for this application
    can_resubmit: bool


class TrackerOut(BaseModel):
    application_id: uuid.UUID
    current_step: str
    steps: list[TrackerStepOut]
    needs_info: NeedsInfoOut | None = None
    decision: BorrowerDecisionOut | None = None
