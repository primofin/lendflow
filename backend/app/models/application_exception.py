"""A mandatory document an officer declared unavailable (LF-007). One per requirement; no text."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ApplicationException(Base):
    __tablename__ = "application_exceptions"
    __table_args__ = (
        UniqueConstraint(
            "application_id", "requirement_id", name="uq_application_exceptions_app_requirement"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), index=True)
    requirement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("required_document_rules.id"))
    declared_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    declared_at: Mapped[datetime]
