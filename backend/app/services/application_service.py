"""Application access rules (LF-002, C-12): ownership checks; staff reads are audited."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import Forbidden, NotFound, UnprocessableEntity
from app.core.permissions import STAFF_ROLES
from app.models.application import Application, ApplicationStatus
from app.models.borrower_profile import BorrowerProfile
from app.models.status_history import StatusHistory
from app.models.user import Role, User
from app.schemas.application import ApplicationSubmitIn, ProfileIn
from app.services import audit_service, consent_service


def submit(
    db: Session, *, user: User, data: ApplicationSubmitIn, now: datetime, ip: str | None
) -> Application:
    """LF-004: validate, record consent, store profile and application as SUBMITTED.

    Every check runs before anything is added, and one commit saves it all, so a rejected
    submission leaves nothing behind (BR-21: no processing before consent).
    """
    consent_service.require_current_version(data.consent_version)
    _check_age(data.profile.date_of_birth, data.term_months, today=now.date())

    consent_given = consent_service.record_consent(db, user=user, now=now)
    profile = _upsert_profile(db, user, data.profile)
    application = Application(
        borrower_profile_id=profile.id,
        created_by=user.id,
        amount_vnd=Decimal(data.amount_vnd),
        term_months=data.term_months,
        purpose=(data.purpose or "").strip() or None,
        status=ApplicationStatus.SUBMITTED.value,
        submitted_at=now,
    )
    db.add(application)
    db.flush()
    db.add(
        StatusHistory(
            application_id=application.id,
            from_status=ApplicationStatus.DRAFT.value,
            to_status=ApplicationStatus.SUBMITTED.value,
            actor_id=user.id,
            changed_at=now,
        )
    )
    if consent_given:
        _audit(db, user, "consent.give", application.id, now, ip, target_type="application")
    _audit(db, user, "application.submit", application.id, now, ip)
    db.commit()
    return application


def _upsert_profile(db: Session, user: User, data: ProfileIn) -> BorrowerProfile:
    profile = db.scalar(select(BorrowerProfile).where(BorrowerProfile.user_id == user.id))
    if profile is None:
        profile = BorrowerProfile(user_id=user.id)
        db.add(profile)
    profile.full_name = data.full_name
    profile.date_of_birth = data.date_of_birth
    profile.national_id = data.national_id
    profile.address = data.address
    profile.income_type = data.income_type.value
    profile.monthly_income_vnd = Decimal(data.monthly_income_vnd)
    profile.existing_debt_payment_vnd = Decimal(data.existing_debt_payment_vnd)
    db.flush()
    return profile


def _years_between(born: date, on: date) -> int:
    return on.year - born.year - ((on.month, on.day) < (born.month, born.day))


def _add_months(day: date, months: int) -> date:
    index = day.month - 1 + months
    year, month = day.year + index // 12, index % 12 + 1
    return date(year, month, min(day.day, 28))


def _check_age(born: date, term_months: int, *, today: date) -> None:
    """BR-03: 18 to 60 at application; maximum 65 (configurable) at maturity."""
    settings = get_settings()
    age = _years_between(born, today)
    if age < settings.min_age_at_application:
        raise UnprocessableEntity(
            f"Applicant must be at least {settings.min_age_at_application} years old"
        )
    if age > settings.max_age_at_application:
        raise UnprocessableEntity(
            f"Applicant must be at most {settings.max_age_at_application} years old "
            "at the time of application"
        )
    if _years_between(born, _add_months(today, term_months)) > settings.max_age_at_maturity:
        raise UnprocessableEntity(
            f"Applicant would be over {settings.max_age_at_maturity} at maturity; "
            "choose a shorter term"
        )


def get_for_user(
    db: Session, *, user: User, application_id: uuid.UUID, now: datetime, ip: str | None
) -> Application:
    """Return the application if `user` may read it (RBAC rule 1, rule 4)."""
    application = db.get(Application, application_id)
    if application is None:
        raise NotFound("Application not found")

    if user.role == Role.BORROWER:
        owner_id = db.scalar(
            select(BorrowerProfile.user_id).where(
                BorrowerProfile.id == application.borrower_profile_id
            )
        )
        if owner_id == user.id:
            return application
        _audit(db, user, "application.access_denied", application.id, now, ip)
        db.commit()
        raise Forbidden()

    if user.role in STAFF_ROLES:
        # LF-010 narrows officers to assigned / queued applications.
        _audit(db, user, "application.read", application.id, now, ip)
        db.commit()
        return application

    raise Forbidden()  # default deny for any future role


def _audit(
    db: Session,
    user: User,
    action: str,
    target_id: uuid.UUID,
    now: datetime,
    ip: str | None,
    target_type: str = "application",
) -> None:
    audit_service.record(
        db,
        action=action,
        now=now,
        actor_id=user.id,
        target_type=target_type,
        target_id=target_id,
        ip_address=ip,
    )
