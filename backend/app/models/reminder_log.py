"""Which repayment reminders were already queued (LF-014), so none is sent twice."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ReminderLog(Base):
    __tablename__ = "reminder_log"
    __table_args__ = (
        UniqueConstraint(
            "application_id", "instalment_number", "kind", name="uq_reminder_log_instalment_kind"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), index=True)
    instalment_number: Mapped[int]
    kind: Mapped[str] = mapped_column(String(10))  # week | day
    sent_at: Mapped[datetime]
