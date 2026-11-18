"""LF-018 data-subject rights (BR-22): view, export, and request deletion of one's own data.

A deletion request is only recorded and tracked. Nothing is deleted here: a person actions it,
and the append-only audit log and decisions (BR-14) are kept regardless. No personal data goes
into audit rows; they hold ids only.
"""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.consent import PURPOSES
from app.core.errors import Conflict
from app.models.application import Application, ApplicationStatus
from app.models.borrower_profile import BorrowerProfile
from app.models.consent import Consent
from app.models.decision import Decision
from app.models.deletion_request import DeletionRequest
from app.models.document import Document
from app.models.user import User
from app.schemas.data_rights import (
    AccountData,
    ApplicationData,
    ConsentData,
    DecisionData,
    DeletionRequestAdminOut,
    DeletionRequestOut,
    DocumentData,
    MyDataExportOut,
    MyDataOut,
    ProfileData,
    PurposeData,
    RetainedItem,
)
from app.services import audit_service

_ACTIVE = frozenset(
    {
        ApplicationStatus.SUBMITTED.value,
        ApplicationStatus.IN_REVIEW.value,
        ApplicationStatus.NEEDS_INFO.value,
        ApplicationStatus.REFERRED.value,
    }
)


def _int(value: object) -> int | None:
    return None if value is None else int(value)  # type: ignore[call-overload]


def _profile(db: Session, user: User) -> BorrowerProfile | None:
    return db.scalar(select(BorrowerProfile).where(BorrowerProfile.user_id == user.id))


def _applications(db: Session, profile: BorrowerProfile | None) -> list[Application]:
    if profile is None:
        return []
    return list(
        db.scalars(
            select(Application)
            .where(Application.borrower_profile_id == profile.id)
            .order_by(Application.created_at.desc(), Application.id)
        )
    )


def _application_data(db: Session, application: Application) -> ApplicationData:
    documents = db.scalars(
        select(Document)
        .where(Document.application_id == application.id)
        .order_by(Document.uploaded_at)
    )
    decisions = db.scalars(
        select(Decision).where(Decision.application_id == application.id).order_by(Decision.seq)
    )
    return ApplicationData(
        id=application.id,
        status=application.status,
        amount_vnd=int(application.amount_vnd),
        term_months=application.term_months,
        purpose=application.purpose,
        submitted_at=application.submitted_at,
        documents=[
            DocumentData(
                doc_type=d.doc_type,
                size_bytes=d.size_bytes,
                uploaded_at=d.uploaded_at,
                delete_after=d.delete_after,
            )
            for d in documents
        ],
        decisions=[
            DecisionData(
                outcome=d.outcome,
                reason_code=d.reason_code,
                explanation=d.explanation,
                conditions=d.conditions,
                decided_at=d.decided_at,
            )
            for d in decisions
        ],
    )


def retained_items(applications: list[Application]) -> list[RetainedItem]:
    """What a deletion request cannot remove yet, and why (AC4, BR-14, BR-23)."""
    items = [
        RetainedItem(
            what=f"Application of {int(a.amount_vnd):,} VND ({a.status.replace('_', ' ').lower()})",
            reason="The application is still being processed; it can be deleted after a final "
            "decision.",
        )
        for a in applications
        if a.status in _ACTIVE
    ]
    items.append(
        RetainedItem(
            what="Audit log entries and recorded decisions",
            reason="They are append-only records that show who did what and when, and are kept "
            "even after a deletion (BR-14).",
        )
    )
    return items


def _request_out(request: DeletionRequest, applications: list[Application]) -> DeletionRequestOut:
    return DeletionRequestOut(
        id=request.id,
        status=request.status,
        requested_at=request.requested_at,
        due_at=request.due_at,
        retained=retained_items(applications) if request.status == "open" else [],
    )


def _latest_request(db: Session, user: User) -> DeletionRequest | None:
    return db.scalars(
        select(DeletionRequest)
        .where(DeletionRequest.user_id == user.id)
        .order_by(DeletionRequest.requested_at.desc())
        .limit(1)
    ).first()


def my_data(db: Session, *, user: User) -> MyDataOut:
    """AC1: every piece of personal data held about the borrower, and the purposes for it."""
    profile = _profile(db, user)
    applications = _applications(db, profile)
    consents = db.scalars(
        select(Consent).where(Consent.user_id == user.id).order_by(Consent.given_at)
    )
    request = _latest_request(db, user)
    return MyDataOut(
        account=AccountData(email=user.email, created_at=user.created_at),
        profile=None
        if profile is None
        else ProfileData(
            full_name=profile.full_name,
            date_of_birth=profile.date_of_birth,
            national_id=profile.national_id,
            address=profile.address,
            income_type=profile.income_type,
            monthly_income_vnd=_int(profile.monthly_income_vnd),
            existing_debt_payment_vnd=_int(profile.existing_debt_payment_vnd),
        ),
        applications=[_application_data(db, a) for a in applications],
        consents=[
            ConsentData(
                version=c.consent_version,
                purposes=list(c.purposes),
                given_at=c.given_at,
                withdrawn_at=c.withdrawn_at,
            )
            for c in consents
        ],
        purposes=[PurposeData(code=p["code"], label=p["label"]) for p in PURPOSES],
        retention_months=get_settings().consent_retention_months,
        deletion_request=None if request is None else _request_out(request, applications),
    )


def export(db: Session, *, user: User, now: datetime, ip: str | None) -> MyDataExportOut:
    """AC2: the same data as a machine-readable file. Never includes password hashes or sessions."""
    data = my_data(db, user=user)
    audit_service.record(
        db,
        action="data.exported",
        now=now,
        actor_id=user.id,
        target_type="user",
        target_id=user.id,
        ip_address=ip,
    )
    db.commit()
    return MyDataExportOut(**data.model_dump(), exported_at=now)


def request_deletion(
    db: Session, *, user: User, now: datetime, ip: str | None
) -> DeletionRequestOut:
    """AC3 and AC4: record a request with a due date, and say what must be retained."""
    existing = db.scalar(
        select(DeletionRequest.id).where(
            DeletionRequest.user_id == user.id, DeletionRequest.status == "open"
        )
    )
    if existing is not None:
        raise Conflict(
            "You already have an open deletion request. We will answer it by its due date."
        )
    request = DeletionRequest(
        user_id=user.id,
        status="open",
        requested_at=now,
        due_at=now + timedelta(days=get_settings().deletion_request_due_days),
    )
    db.add(request)
    db.flush()
    audit_service.record(
        db,
        action="data.deletion_requested",
        now=now,
        actor_id=user.id,
        target_type="deletion_request",
        target_id=request.id,
        ip_address=ip,
    )
    db.commit()
    return _request_out(request, _applications(db, _profile(db, user)))


def list_requests(db: Session, *, now: datetime) -> list[DeletionRequestAdminOut]:
    """AC3: for supervisors, oldest due date first."""
    rows = db.execute(
        select(DeletionRequest, User.email)
        .join(User, User.id == DeletionRequest.user_id)
        .order_by(DeletionRequest.due_at, DeletionRequest.requested_at)
    )
    return [
        DeletionRequestAdminOut(
            id=r.id,
            user_id=r.user_id,
            email=email,
            status=r.status,
            requested_at=r.requested_at,
            due_at=r.due_at,
            overdue=r.status == "open" and r.due_at < now,
        )
        for r, email in rows
    ]
