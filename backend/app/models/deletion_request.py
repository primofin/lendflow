"""A borrower's request to delete their personal data (LF-018, BR-22). Only a person resolves it."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DeletionRequest(Base):
    __tablename__ = "deletion_requests"
    __table_args__ = (
        # One open request per borrower: asking twice never creates a second one.
        Index(
            "uq_deletion_requests_one_open_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(10), default="open")  # open | resolved
    requested_at: Mapped[datetime]
    due_at: Mapped[datetime]
    resolved_at: Mapped[datetime | None]
