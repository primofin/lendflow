"""LF-020 disbursement with a simulated face match for large amounts (C-07).

Disbursing is a human action on an APPROVED application (BR-15 is untouched: nothing here
approves anything). Above `biometric_threshold_vnd` the request must carry a passed, unexpired,
unused face match for the same application. A refusal is audited and committed before the error
is raised, so the attempt leaves a trace. The face match is a simulation: no image is captured.
"""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import Conflict, Forbidden
from app.models.application import Application, ApplicationStatus
from app.models.disbursement import Disbursement, FaceMatch
from app.models.user import User
from app.schemas.disbursement import (
    DisbursementIn,
    DisbursementOut,
    DisbursementStatusOut,
    FaceMatchIn,
    FaceMatchOut,
)
from app.services import application_service, audit_service


def _load(
    db: Session, user: User, application_id: uuid.UUID, now: datetime, ip: str | None
) -> Application:
    return application_service.get_for_user(
        db, user=user, application_id=application_id, now=now, ip=ip, audit_read=False
    )


def _existing(db: Session, application_id: uuid.UUID) -> Disbursement | None:
    return db.scalar(select(Disbursement).where(Disbursement.application_id == application_id))


def _out(d: Disbursement) -> DisbursementOut:
    return DisbursementOut(
        id=d.id,
        application_id=d.application_id,
        amount_vnd=int(d.amount_vnd),
        face_match_id=d.face_match_id,
        disbursed_by=d.disbursed_by,
        disbursed_at=d.disbursed_at,
    )


def needs_face_match(amount_vnd: int) -> bool:
    return amount_vnd > get_settings().biometric_threshold_vnd


def status(
    db: Session, *, user: User, application_id: uuid.UUID, now: datetime, ip: str | None
) -> DisbursementStatusOut:
    application = _load(db, user, application_id, now, ip)
    existing = _existing(db, application.id)
    amount = int(application.amount_vnd)
    return DisbursementStatusOut(
        disbursement=_out(existing) if existing else None,
        amount_vnd=amount,
        face_match_required=needs_face_match(amount),
        threshold_vnd=get_settings().biometric_threshold_vnd,
    )


def simulate_face_match(
    db: Session,
    *,
    user: User,
    application_id: uuid.UUID,
    data: FaceMatchIn,
    now: datetime,
    ip: str | None,
) -> FaceMatchOut:
    application = _load(db, user, application_id, now, ip)
    _require_approved(application)
    if not needs_face_match(int(application.amount_vnd)):
        raise Conflict("This amount does not need a face match")
    match = FaceMatch(
        application_id=application.id,
        performed_by=user.id,
        passed=data.result == "pass",
        created_at=now,
    )
    db.add(match)
    db.flush()
    audit_service.record(
        db,
        action="face_match.passed" if match.passed else "face_match.failed",
        now=now,
        actor_id=user.id,
        target_type="face_match",
        target_id=match.id,
        application_id=application.id,
        ip_address=ip,
    )
    db.commit()
    return FaceMatchOut(
        id=match.id,
        passed=match.passed,
        expires_at=now + timedelta(minutes=get_settings().face_match_ttl_minutes),
    )


def disburse(
    db: Session,
    *,
    user: User,
    application_id: uuid.UUID,
    data: DisbursementIn,
    now: datetime,
    ip: str | None,
) -> DisbursementOut:
    application = _load(db, user, application_id, now, ip)
    db.refresh(application, with_for_update=True)  # one payout per file, even on a double click
    _require_approved(application)
    if _existing(db, application.id) is not None:
        raise Conflict("This loan has already been disbursed")
    amount = int(application.amount_vnd)

    match_id: uuid.UUID | None = None
    if needs_face_match(amount):
        match = _usable_match(db, application.id, data.face_match_id, now)
        if isinstance(match, str):
            audit_service.record(
                db,
                action="disbursement.blocked",
                now=now,
                actor_id=user.id,
                target_type="application",
                target_id=application.id,
                application_id=application.id,
                ip_address=ip,
            )
            db.commit()  # keep the trace of the refused attempt
            raise Forbidden(match)
        match.consumed_at = now
        match_id = match.id

    disbursement = Disbursement(
        application_id=application.id,
        amount_vnd=amount,
        disbursed_by=user.id,
        face_match_id=match_id,
        disbursed_at=now,
    )
    db.add(disbursement)
    db.flush()
    audit_service.record(
        db,
        action="disbursement.created",
        now=now,
        actor_id=user.id,
        target_type="disbursement",
        target_id=disbursement.id,
        application_id=application.id,
        ip_address=ip,
    )
    db.commit()
    return _out(disbursement)


def _require_approved(application: Application) -> None:
    if application.status != ApplicationStatus.APPROVED:
        raise Conflict(
            f"This application is {application.status}. Only APPROVED applications are disbursed."
        )


def _usable_match(
    db: Session, application_id: uuid.UUID, match_id: uuid.UUID | None, now: datetime
) -> FaceMatch | str:
    """The face match if it can be used, otherwise the reason it cannot (shown to the user)."""
    amount_note = f"above {get_settings().biometric_threshold_vnd:,} VND"
    if match_id is None:
        return f"Disbursements {amount_note} need a face match. Complete the face-match step first."
    match = db.get(FaceMatch, match_id, with_for_update=True)
    if match is None or match.application_id != application_id:
        return "This face match does not belong to this application. Run a new face match."
    if not match.passed:
        return "The face match failed, so the disbursement is blocked. Run a new face match."
    if match.consumed_at is not None:
        return "This face match was already used. Run a new face match."
    ttl = timedelta(minutes=get_settings().face_match_ttl_minutes)
    if now - match.created_at > ttl:
        return "This face match has expired. Run a new face match."
    return match
