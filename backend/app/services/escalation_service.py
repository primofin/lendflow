"""LF-007 supervisor escalation (BR-10): flag a file as an exception and assign a supervisor.

Assignment goes to the active supervisor with the fewest open exception files, the one with
the oldest account winning ties. LF-010 (queues) can replace this rule.
"""

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.application import Application, ApplicationStatus
from app.models.requirement_rules import IncomeTypeRule
from app.models.user import Role, User
from app.services import audit_service

OPEN_STATUSES = (ApplicationStatus.SUBMITTED.value,)


def pick_supervisor(db: Session) -> uuid.UUID | None:
    open_exceptions = (
        select(func.count())
        .select_from(Application)
        .where(
            Application.assigned_supervisor == User.id,
            Application.exception_flag.is_(True),
            Application.status.in_(OPEN_STATUSES),
        )
        .correlate(User)
        .scalar_subquery()
    )
    return db.scalar(
        select(User.id)
        .where(User.role == Role.SUPERVISOR, User.is_active.is_(True))
        .order_by(open_exceptions, User.created_at, User.id)
        .limit(1)
    )


def flag_and_assign(
    db: Session, application: Application, *, actor_id: uuid.UUID, now: datetime, ip: str | None
) -> None:
    """Mark the file as an exception and, if it has none yet, assign a supervisor."""
    application.exception_flag = True
    if application.assigned_supervisor is not None:
        return
    supervisor_id = pick_supervisor(db)
    if supervisor_id is None:  # no active supervisor: the flag still holds, a human must pick up
        return
    application.assigned_supervisor = supervisor_id
    audit_service.record(
        db,
        action="application.supervisor_assigned",
        now=now,
        actor_id=actor_id,
        target_type="application",
        target_id=application.id,
        application_id=application.id,
        ip_address=ip,
    )


def escalate_on_submit(
    db: Session, application: Application, *, actor_id: uuid.UUID, now: datetime, ip: str | None
) -> None:
    """Income types such as "Other" always go to a supervisor (docs/02)."""
    if application.income_type is None:
        return
    rule = db.get(IncomeTypeRule, application.income_type)
    if rule is not None and rule.supervisor_always:
        flag_and_assign(db, application, actor_id=actor_id, now=now, ip=ip)
