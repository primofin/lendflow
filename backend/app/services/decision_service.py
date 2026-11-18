"""LF-011 decisions: approve, reject, request information, refer (BR-12 to BR-15).

The AI only recommends. A status of APPROVED or REJECTED comes into existence here and nowhere
else, and only as the result of a human's decision row (BR-15). Decisions are never edited; a
correction by a supervisor is a new row that supersedes the old one (BR-14).
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import Conflict, Forbidden, UnprocessableEntity
from app.core.permissions import check_decision_authority
from app.models.application import Application, ApplicationStatus
from app.models.decision import Decision, ReasonCode
from app.models.status_history import StatusHistory
from app.models.user import Role, User
from app.schemas.decision import BorrowerDecisionOut, DecisionIn, DecisionOut
from app.services import (
    application_service,
    audit_service,
    escalation_service,
    notification_service,
)

S = ApplicationStatus

# docs/03 state machine: outcome -> (statuses it may be recorded from, resulting status)
_TRANSITIONS: dict[str, tuple[frozenset[str], str]] = {
    "approve": (frozenset({S.IN_REVIEW, S.REFERRED}), S.APPROVED),
    "reject": (frozenset({S.IN_REVIEW, S.REFERRED}), S.REJECTED),
    "request_info": (frozenset({S.IN_REVIEW, S.REFERRED}), S.NEEDS_INFO),
    "refer": (frozenset({S.IN_REVIEW}), S.REFERRED),
}
_FINAL_OUTCOMES = frozenset({"approve", "reject"})
_EMAIL_EVENT = {"approve": "approved", "reject": "rejected", "request_info": "info_requested"}


def list_reason_codes(db: Session) -> list[ReasonCode]:
    return list(
        db.scalars(
            select(ReasonCode).where(ReasonCode.active.is_(True)).order_by(ReasonCode.sort_order)
        )
    )


def decide(
    db: Session,
    *,
    user: User,
    application_id: uuid.UUID,
    data: DecisionIn,
    now: datetime,
    ip: str | None,
) -> Decision:
    application = application_service.get_for_user(
        db, user=user, application_id=application_id, now=now, ip=ip, audit_read=False
    )
    db.refresh(application, with_for_update=True)  # two staff cannot decide the same file at once
    latest = _latest(db, application.id)
    previous_status = application.status

    if data.supersedes_id is not None:
        _check_correction(user, latest, data)
        if data.outcome not in _FINAL_OUTCOMES:
            raise UnprocessableEntity("A correction must be an approval or a rejection")
        new_status = S(_TRANSITIONS[data.outcome][1])
    else:
        new_status = _check_transition(application, user, data.outcome)
    reason = _check_reason_code(db, data)
    if data.outcome == "approve":  # BR-10
        check_decision_authority(
            user.role, application.amount_vnd, exception_flag=application.exception_flag
        )

    decision = Decision(
        application_id=application.id,
        decided_by=user.id,
        outcome=data.outcome,
        reason_code=reason,
        explanation=data.explanation,
        conditions=data.conditions,
        supersedes_id=data.supersedes_id,
        decided_at=now,
    )
    db.add(decision)
    db.flush()
    application.status = new_status.value
    if user.role == Role.OFFICER and application.assigned_officer is None:
        application.assigned_officer = user.id
    if data.outcome == "refer":
        escalation_service.assign_supervisor(db, application, actor_id=user.id, now=now, ip=ip)
    db.add(
        StatusHistory(
            application_id=application.id,
            from_status=previous_status,
            to_status=new_status.value,
            actor_id=user.id,
            changed_at=now,
        )
    )
    # Ids and actions only: the explanation is text a person typed and stays out of the log.
    audit_service.record(
        db,
        action="decision.correct" if data.supersedes_id else f"decision.{data.outcome}",
        now=now,
        actor_id=user.id,
        target_type="decision",
        target_id=decision.id,
        application_id=application.id,
        ip_address=ip,
    )
    if data.outcome != "refer":  # a referral is internal; the borrower is not told
        notification_service.notify(db, application, _EMAIL_EVENT[data.outcome], now=now)
    db.commit()
    return decision


def _check_transition(application: Application, user: User, outcome: str) -> ApplicationStatus:
    allowed_from, result = _TRANSITIONS[outcome]
    current = application.status
    if current in (S.APPROVED, S.REJECTED):
        raise Conflict(
            f"This application is already {current}. Only a supervisor can correct a decision, "
            "by sending the id of the decision it replaces."
        )
    if current not in allowed_from:
        raise Conflict(
            f"This application is {current}, so it cannot be recorded as '{outcome}'. "
            "Decisions are made on files that are IN_REVIEW or REFERRED."
        )
    if current == S.REFERRED and user.role != Role.SUPERVISOR:
        raise Forbidden("This file was referred to a supervisor; only a supervisor can decide it")
    if outcome == "refer" and user.role != Role.OFFICER:
        raise Forbidden("Only an officer refers a file; a supervisor decides it directly")
    return S(result)


def _check_correction(user: User, latest: Decision | None, data: DecisionIn) -> None:
    if user.role != Role.SUPERVISOR:
        raise Forbidden("Only a supervisor can correct a decision")
    if latest is None or latest.id != data.supersedes_id:
        raise Conflict("Only the most recent decision on an application can be corrected")
    if latest.outcome not in _FINAL_OUTCOMES:
        raise Conflict("Only an approval or a rejection can be corrected")


def _check_reason_code(db: Session, data: DecisionIn) -> str | None:
    if data.reason_code is None:
        return None
    codes = [c.code for c in list_reason_codes(db)]
    if data.reason_code not in codes:
        raise UnprocessableEntity(
            f"Unknown reason code '{data.reason_code}'. Allowed: {', '.join(codes)}"
        )
    return data.reason_code


def _latest(db: Session, application_id: uuid.UUID) -> Decision | None:
    return db.scalar(
        select(Decision)
        .where(Decision.application_id == application_id)
        .order_by(Decision.seq.desc())
        .limit(1)
    )


def claim(
    db: Session, *, officer: User, application_id: uuid.UUID, now: datetime, ip: str | None
) -> Application:
    """An officer takes a queued file so colleagues stop seeing it. Idempotent for the owner."""
    application = application_service.get_for_user(
        db, user=officer, application_id=application_id, now=now, ip=ip, audit_read=False
    )
    db.refresh(application, with_for_update=True)
    if application.assigned_officer == officer.id:
        return application
    if application.status != S.IN_REVIEW:
        raise Conflict("Only files that are IN_REVIEW can be claimed")
    application.assigned_officer = officer.id
    audit_service.record(
        db,
        action="application.claimed",
        now=now,
        actor_id=officer.id,
        target_type="application",
        target_id=application.id,
        application_id=application.id,
        ip_address=ip,
    )
    db.commit()
    return application


def list_decisions(
    db: Session,
    *,
    user: User,
    application_id: uuid.UUID,
    now: datetime,
    ip: str | None,
    audit_read: bool = True,
) -> list[DecisionOut]:
    """Every entry, oldest first, including corrected ones (BR-14). Staff only."""
    application = application_service.get_for_user(
        db, user=user, application_id=application_id, now=now, ip=ip, audit_read=audit_read
    )
    rows = list(
        db.scalars(
            select(Decision).where(Decision.application_id == application.id).order_by(Decision.seq)
        )
    )
    replaced_by = {d.supersedes_id: d.id for d in rows if d.supersedes_id is not None}
    return [
        DecisionOut(
            id=d.id,
            application_id=d.application_id,
            outcome=d.outcome,  # type: ignore[arg-type]
            reason_code=d.reason_code,
            explanation=d.explanation,
            conditions=d.conditions,
            supersedes_id=d.supersedes_id,
            superseded_by=replaced_by.get(d.id),
            decided_by=d.decided_by,
            decided_at=d.decided_at,
        )
        for d in rows
    ]


def borrower_view(db: Session, application: Application) -> BorrowerDecisionOut | None:
    """BR-13: the latest outcome, with its explanation and conditions for a rejection.

    A referral is internal and not shown. Who decided, and internal notes on an approval, never
    reach the borrower.
    """
    latest = _latest(db, application.id)
    if latest is None or latest.outcome == "refer":
        return None
    label = None
    if latest.reason_code is not None:
        reason = db.get(ReasonCode, latest.reason_code)
        label = reason.label if reason else None
    shows_words = latest.outcome in ("reject", "request_info")
    return BorrowerDecisionOut(
        outcome=latest.outcome,  # type: ignore[arg-type]
        reason_label=label,
        explanation=latest.explanation if shows_words else None,
        conditions=latest.conditions,
        decided_at=latest.decided_at,
    )
