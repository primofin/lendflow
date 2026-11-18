"""Mock credit-bureau (CIC) check for an application (LF-008, docs/06 CIC_CHECKS)."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CicCheck(Base):
    __tablename__ = "cic_checks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), index=True)
    started_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(10))  # running | done | timeout
    attempt: Mapped[int] = mapped_column(default=1)
    started_at: Mapped[datetime]
    attempt_started_at: Mapped[datetime]
    finished_at: Mapped[datetime | None]
    debt_group: Mapped[int | None]  # 1 to 5 (C-10)
