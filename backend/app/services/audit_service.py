"""Append-only audit recording (BR-14, LF-016). Never log personal data or secrets here."""

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def record(
    db: Session,
    *,
    action: str,
    now: datetime,
    actor_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
    ip_address: str | None = None,
) -> None:
    """Add an audit row to the current transaction. The caller commits."""
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            ip_address=ip_address,
            created_at=now,
        )
    )
