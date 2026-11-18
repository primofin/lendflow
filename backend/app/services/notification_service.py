"""LF-012 status-change emails, written to the mock outbox in the caller's transaction.

If the status change rolls back, so does the message. Bodies hold the step and a link only:
no amounts, names, or decision text (data minimisation, C-12).
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.application import Application
from app.models.borrower_profile import BorrowerProfile
from app.models.outbox import OutboxMessage
from app.services import audit_service
from app.services.tracker_steps import step_label

# event -> (subject, what happened). The tracker step is added from the application's status.
_EVENTS: dict[str, tuple[str, str]] = {
    "queued": (
        "We are reviewing your application",
        "We have your documents and an officer will now review your application.",
    ),
    "approved": ("Your application was approved", "Your application has been approved."),
    "rejected": (
        "A decision on your application",
        "A decision has been made on your application. Sign in to read the explanation and "
        "what could change the result.",
    ),
    "info_requested": (
        "We need more information",
        "We need more information to continue. Sign in to see what to add.",
    ),
    "reminder_week": (
        "A repayment is due soon",
        "An instalment on your loan is due within a week.",
    ),
    "reminder_day": (
        "A repayment is due tomorrow",
        "An instalment on your loan is due tomorrow.",
    ),
    "resubmitted": (
        "We received your information",
        "Thank you. We received your additional information and an officer will review it.",
    ),
}


def notify_staff(
    db: Session,
    application: Application,
    *,
    recipient_id: uuid.UUID,
    template: str,
    subject: str,
    message: str,
    now: datetime,
) -> None:
    """Queue one email to a staff member about a file. The body holds a step and a link only."""
    link = f"{get_settings().app_base_url}/review/{application.id}"
    row = OutboxMessage(
        recipient_user_id=recipient_id,
        application_id=application.id,
        template=template,
        subject=subject,
        body=f"{message}\n\nStatus: {step_label(application.status)}\nFile: {link}\n",
        created_at=now,
    )
    db.add(row)
    db.flush()
    audit_service.record(
        db,
        action="notification.queued",
        now=now,
        target_type="outbox",
        target_id=row.id,
        application_id=application.id,
    )


def notify(
    db: Session,
    application: Application,
    event: str,
    *,
    now: datetime,
    detail: str | None = None,
) -> uuid.UUID | None:
    """Queue one email to the application's owner. Returns the message id, or None if the
    owner cannot be found."""
    recipient = db.scalar(
        select(BorrowerProfile.user_id).where(BorrowerProfile.id == application.borrower_profile_id)
    )
    if recipient is None:
        return None
    subject, message = _EVENTS[event]
    link = f"{get_settings().app_base_url}/applications/{application.id}"
    extra = f"{detail}\n\n" if detail else ""
    message_row = OutboxMessage(
        recipient_user_id=recipient,
        application_id=application.id,
        template=event,
        subject=subject,
        body=f"{message}\n\n{extra}Status: {step_label(application.status)}\nDetails: {link}\n",
        created_at=now,
    )
    db.add(message_row)
    db.flush()
    audit_service.record(
        db,
        action="notification.queued",
        now=now,
        target_type="outbox",
        target_id=message_row.id,
        application_id=application.id,
    )
    return message_row.id
