"""LF-012 borrower status tracker and resubmission after a request for information."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import Conflict
from app.models.application import Application, ApplicationStatus
from app.models.decision import Decision
from app.models.status_history import StatusHistory
from app.models.user import User
from app.schemas.tracker import MissingItemOut, NeedsInfoOut, StepState, TrackerOut, TrackerStepOut
from app.services import (
    application_service,
    audit_service,
    decision_service,
    notification_service,
    requirements_service,
)
from app.services.tracker_steps import STEPS, step_index, step_label


def tracker(
    db: Session, *, user: User, application_id: uuid.UUID, now: datetime, ip: str | None
) -> TrackerOut:
    application = application_service.get_for_user(
        db, user=user, application_id=application_id, now=now, ip=ip
    )
    current = step_index(application.status)
    last_update = _last_update_by_step(db, application.id)

    steps = []
    for index, (label, _) in enumerate(STEPS):
        state: StepState
        if current < 0 or index > current:
            state = "upcoming"
        elif index == current:
            state = "current"
        else:
            state = "done" if index in last_update else "skipped"
        steps.append(
            TrackerStepOut(
                label=label,
                state=state,
                updated_at=last_update.get(index) if state in ("done", "current") else None,
            )
        )
    return TrackerOut(
        application_id=application.id,
        current_step=step_label(application.status),
        steps=steps,
        needs_info=_needs_info(db, application),
        decision=decision_service.borrower_view(db, application),
    )


def _last_update_by_step(db: Session, application_id: uuid.UUID) -> dict[int, datetime]:
    """Most recent time the file entered each step, from the status history."""
    result: dict[int, datetime] = {}
    rows = db.execute(
        select(StatusHistory.to_status, StatusHistory.changed_at)
        .where(StatusHistory.application_id == application_id)
        .order_by(StatusHistory.changed_at)
    )
    for to_status, changed_at in rows:
        index = step_index(to_status)
        if index >= 0:
            result[index] = changed_at
    return result


def _needs_info(db: Session, application: Application) -> NeedsInfoOut | None:
    if application.status != ApplicationStatus.NEEDS_INFO:
        return None
    missing = _missing_mandatory(db, application)
    request = db.scalar(
        select(Decision)
        .where(Decision.application_id == application.id, Decision.outcome == "request_info")
        .order_by(Decision.seq.desc())
        .limit(1)
    )
    return NeedsInfoOut(
        message=request.explanation if request else None,
        missing_documents=[
            MissingItemOut(label=item.rule.label, accepted_types=sorted(item.rule.doc_types))
            for item in missing
        ],
        upload_url=f"/applications/{application.id}/documents",
        can_resubmit=not missing,
    )


def _missing_mandatory(
    db: Session, application: Application
) -> list[requirements_service.ChecklistItem]:
    result = requirements_service.evaluate_application(db, application)
    return [i for i in result.items if i.rule.mandatory and i.state == "missing"]


def resubmit(
    db: Session, *, user: User, application_id: uuid.UUID, now: datetime, ip: str | None
) -> Application:
    """The borrower answers a request for information: the file returns to the officer.

    The file goes back to IN_REVIEW, not SUBMITTED, because the officer has already looked at
    it, and keeps its officer so the same person gets it back.
    """
    application = application_service.get_for_user(
        db, user=user, application_id=application_id, now=now, ip=ip, audit_read=False
    )
    db.refresh(application, with_for_update=True)
    if application.status != ApplicationStatus.NEEDS_INFO:
        raise Conflict(
            "Only an application that is waiting for more information can be resubmitted"
        )
    missing = _missing_mandatory(db, application)
    if missing:
        labels = "; ".join(item.rule.label for item in missing)
        raise Conflict(f"Add these required documents before resubmitting: {labels}")

    application.status = ApplicationStatus.IN_REVIEW.value
    if application.assigned_supervisor is not None:
        # LF-017: time spent waiting for the borrower does not count against the supervisor
        application.assigned_supervisor_at = now
        application.sla_breached_at = None
    db.add(
        StatusHistory(
            application_id=application.id,
            from_status=ApplicationStatus.NEEDS_INFO.value,
            to_status=ApplicationStatus.IN_REVIEW.value,
            actor_id=user.id,
            changed_at=now,
        )
    )
    audit_service.record(
        db,
        action="application.resubmit",
        now=now,
        actor_id=user.id,
        target_type="application",
        target_id=application.id,
        application_id=application.id,
        ip_address=ip,
    )
    notification_service.notify(db, application, "resubmitted", now=now)
    db.commit()
    return application
