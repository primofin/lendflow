"""LF-013 CSV import: the result an officer sees. Messages never repeat the submitted values."""

import uuid
from typing import Literal

from pydantic import BaseModel


class ImportRowIssue(BaseModel):
    row: int  # 2 is the first data row (row 1 is the header)
    kind: Literal["invalid", "duplicate"]
    message: str


class ImportedRow(BaseModel):
    row: int
    application_id: uuid.UUID


class ImportResultOut(BaseModel):
    job_id: uuid.UUID
    total_rows: int
    imported: int
    duplicates: int
    invalid: int
    issues: list[ImportRowIssue]
    created: list[ImportedRow]
