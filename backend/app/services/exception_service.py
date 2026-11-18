"""LF-007 AC3: an officer declares a mandatory document unavailable ("No invoices available")."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound
from app.models.application import Application, ApplicationStatus
from app.models.application_exception import ApplicationException
from app.models.requirement_rules import RequiredDocumentRule
from app.models.user import User
from app.services import application_service, audit_service, escalation_service
from app.services.requirements_service import (
    application_income_type,
    evaluate_application,
    get_income_rule,
)


def declare(
    db: Session,
    *,
    officer: User,
    application_id: uuid.UUID,
    requirement_id: uuid.UUID,
    now: datetime,
    ip: str | None,
) -> tuple[Application, bool]:
    """Returns (application, created). Re-declaring the same requirement is a no-op."""
    application = application_service.get_for_user(
        db, user=officer, application_id=application_id, now=now, ip=ip, audit_read=False
    )
    income_type = application_income_type(application)
    rule = db.scalar(
        select(RequiredDocumentRule).where(
            RequiredDocumentRule.id == requirement_id,
            RequiredDocumentRule.income_type == income_type,
        )
    )
    if rule is None:
        raise NotFound("Requirement not found for this application")

    existing = _find(db, application.id, rule.id)
    if existing is not None:
        return application, False
    if application.status != ApplicationStatus.SUBMITTED.value:
        raise Conflict("Exceptions can no longer be declared on this application.")
    if not rule.mandatory:
        raise Conflict("This document is optional, so it cannot be declared unavailable.")
    satisfied = {
        item.rule.id
        for item in evaluate_application(db, application).items
        if item.state == "satisfied"
    }
    if rule.id in satisfied:
        raise Conflict("A matching document has already been uploaded; this is already satisfied.")

    db.add(
        ApplicationException(
            application_id=application.id,
            requirement_id=rule.id,
            declared_by=officer.id,
            declared_at=now,
        )
    )
    try:
        db.flush()
    except IntegrityError:  # a concurrent identical declaration won
        db.rollback()
        return application, False
    audit_service.record(
        db,
        action="application.exception_declared",
        now=now,
        actor_id=officer.id,
        target_type="application",
        target_id=application.id,
        application_id=application.id,
        ip_address=ip,
    )
    if get_income_rule(db, income_type).needs_supervisor_if_missing:
        escalation_service.flag_and_assign(db, application, actor_id=officer.id, now=now, ip=ip)
    db.commit()
    return application, True


def _find(db: Session, application_id: uuid.UUID, requirement_id: uuid.UUID) -> object | None:
    return db.scalar(
        select(ApplicationException.id).where(
            ApplicationException.application_id == application_id,
            ApplicationException.requirement_id == requirement_id,
        )
    )
