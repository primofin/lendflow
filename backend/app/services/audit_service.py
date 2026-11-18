"""Append-only audit recording and search (BR-14, LF-016). Never log personal data or secrets."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import Role, User


def record(
    db: Session,
    *,
    action: str,
    now: datetime,
    actor_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
    application_id: uuid.UUID | None = None,
    ip_address: str | None = None,
) -> None:
    """Add an audit row to the current transaction. The caller commits.

    Pass `application_id` whenever the entry concerns an application or one of its documents,
    so the application's full history can be found with one query.
    """
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            application_id=application_id,
            ip_address=ip_address,
            created_at=now,
        )
    )


def search(
    db: Session,
    *,
    viewer: User,
    application_id: uuid.UUID | None,
    actor_id: uuid.UUID | None,
    action: str | None,
    created_from: datetime | None,
    created_to: datetime | None,
    limit: int,
    offset: int,
) -> Sequence[tuple[AuditLog, str | None, Role | None]]:
    """Entries oldest first, in exact insertion order. Only supervisors see other people's.

    Officers are limited to their own actions here, in the query itself, so no combination of
    filters can widen what they see (docs/01 permission matrix).
    """
    statement = (
        select(AuditLog, User.email, User.role)
        .join(User, User.id == AuditLog.actor_id, isouter=True)
        .order_by(AuditLog.seq)
        .limit(limit)
        .offset(offset)
    )
    if viewer.role != Role.SUPERVISOR:
        statement = statement.where(AuditLog.actor_id == viewer.id)
    if application_id is not None:
        statement = statement.where(AuditLog.application_id == application_id)
    if actor_id is not None:
        statement = statement.where(AuditLog.actor_id == actor_id)
    if action is not None:
        statement = statement.where(AuditLog.action == action)
    if created_from is not None:
        statement = statement.where(AuditLog.created_at >= created_from)
    if created_to is not None:
        statement = statement.where(AuditLog.created_at <= created_to)
    return [(row[0], row[1], row[2]) for row in db.execute(statement)]
