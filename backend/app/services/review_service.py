"""F4: the staff file view. Access rules and the read audit come from get_for_user."""

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.models.application import Application
from app.models.borrower_profile import BorrowerProfile
from app.models.user import User
from app.schemas.review import ApplicantOut, Flag, ReviewOut
from app.services import application_service


def mask_national_id(value: str | None) -> str | None:
    """Keep the last four digits only: staff confirm identity from the documents."""
    if not value:
        return None
    return "*" * max(len(value) - 4, 0) + value[-4:]


def _int(value: object) -> int | None:
    return None if value is None else int(value)  # type: ignore[call-overload]


def review(
    db: Session, *, user: User, application_id: uuid.UUID, now: datetime, ip: str | None
) -> ReviewOut:
    application = application_service.get_for_user(
        db, user=user, application_id=application_id, now=now, ip=ip
    )
    profile = db.get(BorrowerProfile, application.borrower_profile_id)
    if profile is None:  # cannot happen: the foreign key guarantees it
        raise NotFound("Application not found")
    return _build(application, profile, user)


def _build(application: Application, profile: BorrowerProfile, user: User) -> ReviewOut:
    flags: list[Flag] = []
    if application.exception_flag:
        flags.append("exception")
    if application.high_dti:
        flags.append("high_dti")
    if application.fast_track:
        flags.append("fast_track")
    rate = application.annual_rate
    return ReviewOut(
        id=application.id,
        status=application.status,
        amount_vnd=int(application.amount_vnd),
        term_months=application.term_months,
        purpose=application.purpose,
        annual_rate_percent=None if rate is None else float(rate * 100),
        submitted_at=application.submitted_at,
        flags=flags,
        assigned_to_me=application.assigned_officer == user.id,
        assigned=application.assigned_officer is not None,
        supervisor_assigned=application.assigned_supervisor is not None,
        applicant=ApplicantOut(
            full_name=profile.full_name,
            date_of_birth=profile.date_of_birth,
            national_id_masked=mask_national_id(profile.national_id),
            address=profile.address,
            income_type=application.income_type or profile.income_type,
            monthly_income_vnd=_int(profile.monthly_income_vnd),
            existing_debt_payment_vnd=_int(profile.existing_debt_payment_vnd),
        ),
    )
