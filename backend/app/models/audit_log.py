"""Append-only audit trail (BR-14, LF-016). See docs/06-data-model.md AUDIT_LOGS.

Only AuditService.record() writes here; there is no update or delete path.
Database-level enforcement and search are delivered in LF-016.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(64))
    target_type: Mapped[str | None] = mapped_column(String(64))
    target_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime]
