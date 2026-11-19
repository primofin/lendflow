"""LF-020 disbursement and simulated face match."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class FaceMatchIn(BaseModel):
    # Simulation only: the caller states the result a real biometric provider would return.
    result: Literal["pass", "fail"]


class FaceMatchOut(BaseModel):
    id: uuid.UUID
    passed: bool
    expires_at: datetime


class DisbursementIn(BaseModel):
    face_match_id: uuid.UUID | None = None


class DisbursementOut(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    amount_vnd: int
    face_match_id: uuid.UUID | None
    disbursed_by: uuid.UUID
    disbursed_at: datetime


class DisbursementStatusOut(BaseModel):
    """What the UI needs to decide whether to show the face-match step."""

    disbursement: DisbursementOut | None
    amount_vnd: int
    face_match_required: bool
    threshold_vnd: int
