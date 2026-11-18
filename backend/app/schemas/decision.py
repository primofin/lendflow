"""LF-011 decisions. Staff see every field; the borrower sees only what BR-13 promises them."""

import uuid
from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

Outcome = Literal["approve", "reject", "request_info", "refer"]

EXPLANATION_MIN = 20
TEXT_MAX = 1000


class DecisionIn(BaseModel):
    outcome: Outcome
    reason_code: str | None = Field(default=None, max_length=40)
    explanation: str | None = Field(default=None, max_length=TEXT_MAX)
    conditions: str | None = Field(default=None, max_length=TEXT_MAX)
    supersedes_id: uuid.UUID | None = None

    @field_validator("reason_code", "explanation", "conditions")
    @classmethod
    def _blank_is_missing(cls, value: str | None) -> str | None:
        value = (value or "").strip()
        return value or None

    @model_validator(mode="after")
    def _outcome_rules(self) -> Self:
        if self.outcome == "reject":  # BR-13
            if self.reason_code is None:
                raise ValueError("A rejection needs a reason code")
            self._need_explanation(
                "A rejection needs a plain-language explanation for the borrower"
            )
            if self.conditions is None:
                raise ValueError(
                    "A rejection must say which documents or conditions could change the outcome"
                )
            return self
        if self.reason_code is not None or self.conditions is not None:
            raise ValueError("Only a rejection carries a reason code and conditions")
        if self.outcome == "request_info":
            self._need_explanation("Say in plain language which information the borrower must add")
        return self

    def _need_explanation(self, message: str) -> None:
        if self.explanation is None or len(self.explanation) < EXPLANATION_MIN:
            raise ValueError(f"{message} (at least {EXPLANATION_MIN} characters)")


class DecisionOut(BaseModel):
    """Staff view of one entry. `superseded_by` shows a correction without hiding the original."""

    id: uuid.UUID
    application_id: uuid.UUID
    outcome: Outcome
    reason_code: str | None
    explanation: str | None
    conditions: str | None
    supersedes_id: uuid.UUID | None
    superseded_by: uuid.UUID | None
    decided_by: uuid.UUID
    decided_at: datetime


class BorrowerDecisionOut(BaseModel):
    """What the borrower may see: the outcome, and for a rejection or a request, the words."""

    outcome: Literal["approve", "reject", "request_info"]
    reason_label: str | None = None
    explanation: str | None = None
    conditions: str | None = None
    decided_at: datetime


class ReasonCodeOut(BaseModel):
    code: str
    label: str
