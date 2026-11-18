"""Uploaded documents (docs/06 DOCUMENTS). The original filename is deliberately not stored."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DocType(enum.StrEnum):
    """Document kinds from docs/02 section 3 (required documents by income type)."""

    NATIONAL_ID = "national_id"
    LABOUR_CONTRACT = "labour_contract"
    PAYSLIPS = "payslips"
    BANK_STATEMENTS = "bank_statements"
    TAX_RETURN = "tax_return"
    INVOICES_CONTRACTS = "invoices_contracts"
    BUSINESS_LICENCE = "business_licence"
    RENTAL_CONTRACT = "rental_contract"
    PROOF_OF_OWNERSHIP = "proof_of_ownership"
    OTHER = "other"


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        # A retried upload of the same bytes as the same type is a duplicate (LF-005 AC4).
        UniqueConstraint(
            "application_id", "doc_type", "sha256", name="uq_documents_application_type_content"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), index=True)
    doc_type: Mapped[str] = mapped_column(String(40))
    storage_key: Mapped[str] = mapped_column(String(80), unique=True)  # random name, not user input
    mime_type: Mapped[str] = mapped_column(String(100))  # detected from content
    size_bytes: Mapped[int]
    sha256: Mapped[str] = mapped_column(String(64))
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    uploaded_at: Mapped[datetime]
    delete_after: Mapped[datetime | None]  # BR-23: set when a final decision exists (LF-011)
