"""Application endpoints. LF-002: read with ownership check; LF-004: submit with consent."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import BorrowerAuth, ClientIp, CurrentAuth, DbSession, Now, require_roles
from app.models.user import Role
from app.schemas.application import ApplicationOut, ApplicationSubmitIn
from app.schemas.cic import CicCheckOut
from app.schemas.decision import DecisionIn, DecisionOut
from app.schemas.review import ReviewOut
from app.schemas.schedule import ScheduleOut
from app.schemas.tracker import TrackerOut
from app.services import (
    application_service,
    cic_service,
    decision_service,
    review_service,
    schedule_service,
    tracker_service,
)
from app.services.auth_service import AuthContext

router = APIRouter(prefix="/applications", tags=["applications"])

StaffAuth = Annotated[AuthContext, Depends(require_roles(Role.OFFICER, Role.SUPERVISOR))]
OfficerAuth = Annotated[AuthContext, Depends(require_roles(Role.OFFICER))]


@router.post("", status_code=status.HTTP_201_CREATED)
def submit_application(
    body: ApplicationSubmitIn, auth: BorrowerAuth, db: DbSession, clock: Now, ip: ClientIp
) -> ApplicationOut:
    """LF-004: borrower submits with consent; nothing is saved unless every rule passes."""
    application = application_service.submit(db, user=auth.user, data=body, now=clock(), ip=ip)
    return ApplicationOut.model_validate(application)


@router.get("")
def list_my_applications(auth: BorrowerAuth, db: DbSession) -> list[ApplicationOut]:
    """Borrower's own applications, newest first, so they can return to the tracker."""
    return [
        ApplicationOut.model_validate(a) for a in application_service.list_mine(db, user=auth.user)
    ]


@router.get("/{application_id}")
def get_application(
    application_id: uuid.UUID, auth: CurrentAuth, db: DbSession, clock: Now, ip: ClientIp
) -> ApplicationOut:
    """LF-002: borrowers see only their own; staff reads are audited."""
    application = application_service.get_for_user(
        db, user=auth.user, application_id=application_id, now=clock(), ip=ip
    )
    out = ApplicationOut.model_validate(application)
    out.decision = decision_service.borrower_view(db, application)  # LF-011, BR-13
    return out


@router.get("/{application_id}/review")
def review_application(
    application_id: uuid.UUID, auth: StaffAuth, db: DbSession, clock: Now, ip: ClientIp
) -> ReviewOut:
    """F4: the file view for staff: loan, applicant (ID masked), flags and who holds it."""
    return review_service.review(
        db, user=auth.user, application_id=application_id, now=clock(), ip=ip
    )


@router.post("/{application_id}/claim")
def claim_application(
    application_id: uuid.UUID, auth: OfficerAuth, db: DbSession, clock: Now, ip: ClientIp
) -> ApplicationOut:
    """LF-011: an officer takes a queued file; other officers then no longer see it."""
    application = decision_service.claim(
        db, officer=auth.user, application_id=application_id, now=clock(), ip=ip
    )
    return ApplicationOut.model_validate(application)


@router.post("/{application_id}/decision", status_code=status.HTTP_201_CREATED)
def record_decision(
    application_id: uuid.UUID,
    body: DecisionIn,
    auth: StaffAuth,
    db: DbSession,
    clock: Now,
    ip: ClientIp,
) -> DecisionOut:
    """LF-011: approve, reject, request information or refer. A human decision (BR-15)."""
    decision = decision_service.decide(
        db, user=auth.user, application_id=application_id, data=body, now=clock(), ip=ip
    )
    entries = decision_service.list_decisions(
        db, user=auth.user, application_id=application_id, now=clock(), ip=ip, audit_read=False
    )
    return next(entry for entry in entries if entry.id == decision.id)


@router.get("/{application_id}/decisions")
def list_decisions(
    application_id: uuid.UUID, auth: StaffAuth, db: DbSession, clock: Now, ip: ClientIp
) -> list[DecisionOut]:
    """LF-011: every decision on the file, oldest first, corrected ones included (BR-14)."""
    return decision_service.list_decisions(
        db, user=auth.user, application_id=application_id, now=clock(), ip=ip
    )


@router.get("/{application_id}/tracker")
def get_tracker(
    application_id: uuid.UUID, auth: CurrentAuth, db: DbSession, clock: Now, ip: ClientIp
) -> TrackerOut:
    """LF-012: where the application is, step by step, and what the borrower must do next."""
    return tracker_service.tracker(
        db, user=auth.user, application_id=application_id, now=clock(), ip=ip
    )


@router.post("/{application_id}/resubmit")
def resubmit_application(
    application_id: uuid.UUID, auth: BorrowerAuth, db: DbSession, clock: Now, ip: ClientIp
) -> TrackerOut:
    """LF-012: the borrower has added what was asked; the file returns to the officer."""
    tracker_service.resubmit(db, user=auth.user, application_id=application_id, now=clock(), ip=ip)
    return tracker_service.tracker(
        db, user=auth.user, application_id=application_id, now=clock(), ip=ip
    )


@router.post("/{application_id}/cic-check", status_code=status.HTTP_201_CREATED)
def start_cic_check(
    application_id: uuid.UUID, auth: StaffAuth, db: DbSession, clock: Now, ip: ClientIp
) -> CicCheckOut:
    """LF-008: start the mock credit-bureau check for a file in review."""
    return cic_service.start(db, user=auth.user, application_id=application_id, now=clock(), ip=ip)


@router.get("/{application_id}/cic-check")
def get_cic_check(
    application_id: uuid.UUID, auth: StaffAuth, db: DbSession, clock: Now, ip: ClientIp
) -> CicCheckOut | None:
    """LF-008: progress or result of the latest check; null when none was started."""
    return cic_service.get_latest(
        db, user=auth.user, application_id=application_id, now=clock(), ip=ip
    )


@router.get("/{application_id}/schedule")
def get_schedule(
    application_id: uuid.UUID, auth: CurrentAuth, db: DbSession, clock: Now, ip: ClientIp
) -> ScheduleOut:
    """LF-014: the repayment schedule of an approved application (owner or staff)."""
    return schedule_service.get_schedule(
        db, user=auth.user, application_id=application_id, now=clock(), ip=ip
    )
