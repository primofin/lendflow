"""Document requirements by income type (BR-06), held as data so rules can change without code.

A requirement is met by ANY of its options (e.g. "labour contract or employer confirmation").
Rows are seeded by migration 0007 from docs/02-business-rules.md section 3; the values are
illustrative and the freelance/self-employed acceptance rule is still open (Q1).
"""

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IncomeTypeRule(Base):
    __tablename__ = "income_type_rules"

    income_type: Mapped[str] = mapped_column(String(20), primary_key=True)
    label: Mapped[str] = mapped_column(String(100))
    # A mandatory document declared unavailable makes the file an exception for a supervisor.
    needs_supervisor_if_missing: Mapped[bool] = mapped_column(default=True)
    # "Other" income always goes to a supervisor (docs/02), documents or not.
    supervisor_always: Mapped[bool] = mapped_column(default=False)


class RequiredDocumentRule(Base):
    __tablename__ = "required_document_rules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    income_type: Mapped[str] = mapped_column(
        ForeignKey("income_type_rules.income_type"), index=True
    )
    label: Mapped[str] = mapped_column(String(150))
    mandatory: Mapped[bool]
    sort_order: Mapped[int]


class RequiredDocumentOption(Base):
    __tablename__ = "required_document_options"

    rule_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("required_document_rules.id"), primary_key=True
    )
    doc_type: Mapped[str] = mapped_column(String(40), primary_key=True)
