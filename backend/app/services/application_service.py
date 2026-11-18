"""Application access rules (LF-002, C-12): ownership checks; staff reads are audited."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import Forbidden, NotFound
from app.core.permissions import STAFF_ROLES
from app.models.application import Application
from app.models.borrower_profile import BorrowerProfile
from app.models.user import Role, User
from app.services import audit_service


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
    db: Session, user: User, action: str, target_id: uuid.UUID, now: datetime, ip: str | None
) -> None:
    audit_service.record(
        db,
        action=action,
        now=now,
        actor_id=user.id,
        target_type="application",
        target_id=target_id,
        ip_address=ip,
    )
