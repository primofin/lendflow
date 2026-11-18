"""LF-014 repayment reminders: an email 7 days and 1 day before each instalment is due.

There is no background worker. `send_due_reminders` looks at every approved application and
queues each reminder that is due now, once (`reminder_log`). It is run by a supervisor from the
app or by `scripts/send_reminders.py` on a schedule. A reminder is due when the instalment is
still ahead and at most 7 days (week) or 1 day (day) away, so a run that was late still sends
the nearest one, and never on or after the due date. A borrower who opted out, or whose account
is inactive, gets nothing. The email holds the instalment number, the date and a link; amounts
stay out of email (C-12). No payments are recorded, so a reminder does not know if one was paid.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.application import Application, ApplicationStatus
from app.models.borrower_profile import BorrowerProfile
from app.models.reminder_log import ReminderLog
from app.models.user import User
from app.services import notification_service, schedule_service

WEEK_DAYS = 7
DAY_DAYS = 1


def _kind(days_left: int) -> str | None:
    if days_left <= 0:
        return None
    if days_left <= DAY_DAYS:
        return "day"
    if days_left <= WEEK_DAYS:
        return "week"
    return None


def send_due_reminders(db: Session, *, now: datetime) -> int:
    """Queue the reminders that are due and not yet sent. Returns how many were queued."""
    today = now.date()
    apps = list(
        db.scalars(
            select(Application)
            .where(Application.status == ApplicationStatus.APPROVED.value)
            .order_by(Application.id)
        )
    )
    starts = schedule_service.approval_dates(db, [a.id for a in apps])
    sent = 0
    for application in apps:
        start = starts.get(application.id)
        owner = _owner(db, application)
        if start is None or owner is None or not owner.is_active or not owner.repayment_reminders:
            continue
        for number in range(1, application.term_months + 1):
            due = schedule_service.due_date(start, number)
            days_left = (due - today).days
            if days_left > WEEK_DAYS:
                break  # later instalments are further away still
            kind = _kind(days_left)
            if kind is None:
                continue
            if _queue(db, application, number, kind, due, now):
                sent += 1
    db.commit()
    return sent


def _owner(db: Session, application: Application) -> User | None:
    owner_id = db.scalar(
        select(BorrowerProfile.user_id).where(BorrowerProfile.id == application.borrower_profile_id)
    )
    return None if owner_id is None else db.get(User, owner_id)


def _queue(
    db: Session, application: Application, number: int, kind: str, due: object, now: datetime
) -> bool:
    already = db.scalar(
        select(ReminderLog.id).where(
            ReminderLog.application_id == application.id,
            ReminderLog.instalment_number == number,
            ReminderLog.kind == kind,
        )
    )
    if already is not None:
        return False
    try:
        with db.begin_nested():  # a concurrent run that logged it first just wins
            db.add(
                ReminderLog(
                    application_id=application.id,
                    instalment_number=number,
                    kind=kind,
                    sent_at=now,
                )
            )
            db.flush()
    except IntegrityError:
        return False
    notification_service.notify(
        db,
        application,
        "reminder_day" if kind == "day" else "reminder_week",
        now=now,
        detail=f"Instalment {number} of {application.term_months} is due on {due:%d %B %Y}.",
    )
    return True
