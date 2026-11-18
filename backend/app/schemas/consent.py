"""Consent screen content (LF-004 AC2)."""

from pydantic import BaseModel


class PurposeOut(BaseModel):
    code: str
    label: str


class ConsentOut(BaseModel):
    version: str
    statement: str
    purposes: list[PurposeOut]
    retention_months: int
