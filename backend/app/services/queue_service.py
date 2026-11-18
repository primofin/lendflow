"""LF-010 officer queue, and the move of ready files into it.

A file is ready for an officer (SUBMITTED -> IN_REVIEW) once every mandatory document is
uploaded or waived. LF-008 (CIC check) will add its own condition before this step.
"""

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.application import Application, ApplicationStatus
from app.models.borrower_profile import BorrowerProfile
from app.models.status_history import StatusHistory
from app.models.user import Role, User
from app.schemas.queue import QueueFlag, QueueItemOut, QueuePageOut, QueueParams
from app.services import audit_service, notification_service, requirements_service, sla_service

EMPTY_MESSAGE = "No applications waiting"

_FLAG_COLUMNS = {
    "exception": Application.exception_flag,
    "high_dti": Application.high_dti,
    "fast_track": Application.fast_track,
    "overdue": Application.sla_breached_at.is_not(None),  # LF-017
}


def promote_if_ready(
    db: Session, application: Application, *, actor_id: uuid.UUID, now: datetime, ip: str | None
) -> bool:
    """Queue the file for an officer when no mandatory document is missing. Caller commits."""
    if application.status != ApplicationStatus.SUBMITTED.value:
        return False
    if requirements_service.evaluate_application(db, application).status == "incomplete":
        return False
    application.status = ApplicationStatus.IN_REVIEW.value
    db.add(
        StatusHistory(
            application_id=application.id,
            from_status=ApplicationStatus.SUBMITTED.value,
            to_status=ApplicationStatus.IN_REVIEW.value,
            actor_id=actor_id,
            changed_at=now,
        )
    )
    audit_service.record(
        db,
        action="application.queued",
        now=now,
        actor_id=actor_id,
        target_type="application",
        target_id=application.id,
        application_id=application.id,
        ip_address=ip,
    )
    notification_service.notify(db, application, "queued", now=now)
    return True


def list_queue(
    db: Session, *, viewer: User, params: QueueParams, now: datetime, ip: str | None
) -> QueuePageOut:
    """Supervisors see every file; officers see unassigned files and their own."""
    sla_service.sweep(db, now=now)  # LF-017: mark and announce newly overdue files first
    conditions = [Application.status == params.status]
    if viewer.role != Role.SUPERVISOR:
        conditions.append(
            Application.assigned_officer.is_(None) | (Application.assigned_officer == viewer.id)
        )
    if params.flag is not None:
        conditions.append(_FLAG_COLUMNS[params.flag].is_(True))

    total = db.scalar(select(func.count()).select_from(Application).where(*conditions)) or 0
    order = Application.submitted_at, Application.id
    rows = db.execute(
        select(Application, BorrowerProfile.full_name)
        .join(BorrowerProfile, BorrowerProfile.id == Application.borrower_profile_id)
        .where(*conditions)
        .order_by(*(c.desc() for c in order) if params.sort == "newest" else order)
        .limit(params.limit)
        .offset(params.offset)
    ).all()

    audit_service.record(
        db, action="queue.view", now=now, actor_id=viewer.id, target_type="queue", ip_address=ip
    )
    db.commit()
    items = [_item(application, name, now) for application, name in rows]
    return QueuePageOut(
        items=items,
        total=total,
        limit=params.limit,
        offset=params.offset,
        message=EMPTY_MESSAGE if total == 0 else None,
    )


def _item(application: Application, name: str | None, now: datetime) -> QueueItemOut:
    flags: list[QueueFlag] = []
    if application.exception_flag:
        flags.append("exception")
    if application.high_dti:
        flags.append("high_dti")
    if application.fast_track:
        flags.append("fast_track")
    if sla_service.is_overdue(application):
        flags.append("overdue")
    age = None
    if application.submitted_at is not None:
        age = round((now - application.submitted_at).total_seconds() / 3600, 2)
    return QueueItemOut(
        id=application.id,
        status=application.status,
        applicant_name=name,
        amount_vnd=int(application.amount_vnd),
        term_months=application.term_months,
        flags=flags,
        submitted_at=application.submitted_at,
        age_hours=age,
    )
