"""LF-018: what a borrower can see, export and request about their own data."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel


class AccountData(BaseModel):
    email: str
    created_at: datetime


class ProfileData(BaseModel):
    full_name: str | None
    date_of_birth: date | None
    national_id: str | None
    address: str | None
    income_type: str | None
    monthly_income_vnd: int | None
    existing_debt_payment_vnd: int | None


class DecisionData(BaseModel):
    outcome: str
    reason_code: str | None
    explanation: str | None
    conditions: str | None
    decided_at: datetime


class DocumentData(BaseModel):
    doc_type: str
    size_bytes: int
    uploaded_at: datetime
    delete_after: datetime | None


class ApplicationData(BaseModel):
    id: uuid.UUID
    status: str
    amount_vnd: int
    term_months: int
    purpose: str | None
    submitted_at: datetime | None
    documents: list[DocumentData]
    decisions: list[DecisionData]


class ConsentData(BaseModel):
    version: str
    purposes: list[str]
    given_at: datetime
    withdrawn_at: datetime | None


class PurposeData(BaseModel):
    code: str
    label: str


class RetainedItem(BaseModel):
    what: str
    reason: str


class DeletionRequestOut(BaseModel):
    id: uuid.UUID
    status: str
    requested_at: datetime
    due_at: datetime
    # What cannot be deleted yet, and why; worked out from the borrower's files right now.
    retained: list[RetainedItem]


class MyDataOut(BaseModel):
    account: AccountData
    profile: ProfileData | None
    applications: list[ApplicationData]
    consents: list[ConsentData]
    purposes: list[PurposeData]
    retention_months: int
    deletion_request: DeletionRequestOut | None


class MyDataExportOut(MyDataOut):
    exported_at: datetime


class DeletionRequestAdminOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    status: str
    requested_at: datetime
    due_at: datetime
    overdue: bool
