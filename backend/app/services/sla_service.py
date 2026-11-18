"""LF-017 supervisor SLA (BR-11): a file waiting at a supervisor too long becomes overdue.

There is no background worker. `sweep` finds files whose wait has passed the limit and marks
each one once: it records `sla_breached_at`, writes an audit row (`sla.breached`, no actor: the
system did it) and queues an email to every active supervisor. It runs when the queue or a file
is read, and `scripts/sla_sweep.py` can run it on a schedule. Running it twice does nothing new.
Overdue is a flag for people: it never moves or decides a file (BR-15).
"""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.application import Application, ApplicationStatus
from app.models.user import Role, User
from app.services import audit_service, notification_service

# Files a supervisor can act on. NEEDS_INFO is waiting for the borrower, so its clock is paused.
WAITING_STATUSES = (ApplicationStatus.IN_REVIEW.value, ApplicationStatus.REFERRED.value)


def is_overdue(application: Application) -> bool:
    return application.sla_breached_at is not None and application.status in WAITING_STATUSES


def sweep(db: Session, *, now: datetime) -> list[uuid.UUID]:
    """Mark newly overdue files, announce them, and commit. Returns the ids marked now."""
    cutoff = now - timedelta(hours=get_settings().supervisor_sla_hours)
    late = list(
        db.scalars(
            select(Application)
            .where(
                Application.assigned_supervisor.is_not(None),
                Application.status.in_(WAITING_STATUSES),
                Application.sla_breached_at.is_(None),
                Application.assigned_supervisor_at < cutoff,  # strictly more than the limit
            )
            .order_by(Application.assigned_supervisor_at, Application.id)
            .with_for_update(skip_locked=True)
        )
    )
    if not late:
        return []
    supervisors = list(
        db.scalars(
            select(User.id)
            .where(User.role == Role.SUPERVISOR, User.is_active.is_(True))
            .order_by(User.created_at, User.id)
        )
    )
    for application in late:
        application.sla_breached_at = now
        audit_service.record(
            db,
            action="sla.breached",
            now=now,
            target_type="application",
            target_id=application.id,
            application_id=application.id,
        )
        for recipient in supervisors:
            notification_service.notify_staff(
                db,
                application,
                recipient_id=recipient,
                template="sla_overdue",
                subject="A file is overdue for supervisor review",
                message="A file has waited longer than the supervisor review limit.",
                now=now,
            )
    db.commit()
    return [a.id for a in late]
