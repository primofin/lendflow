"""LF-007 schemas: the requirements panel, the checklist and the exception request."""

import uuid
from typing import Literal

from pydantic import BaseModel


class RequirementOut(BaseModel):
    id: uuid.UUID
    label: str
    doc_types: list[str]  # any one of these satisfies the requirement


class PanelOut(BaseModel):
    income_type: str
    label: str
    supervisor_always: bool
    needs_supervisor_if_missing: bool
    mandatory: list[RequirementOut]
    optional: list[RequirementOut]


class ChecklistRequirementOut(BaseModel):
    id: uuid.UUID
    label: str
    mandatory: bool
    state: Literal["satisfied", "waived", "missing"]
    doc_types: list[str]
    document_ids: list[uuid.UUID]


class ChecklistOut(BaseModel):
    application_id: uuid.UUID
    income_type: str
    status: Literal["complete", "exception", "incomplete"]
    requirements: list[ChecklistRequirementOut]
    exception_flag: bool
    supervisor_assigned: bool  # whether, not who: identities are not exposed to borrowers


class ExceptionDeclareIn(BaseModel):
    """Only the requirement is accepted: no free text, so no personal data can slip in."""

    requirement_id: uuid.UUID
