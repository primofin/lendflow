"""LF-014 repayment schedule for an approved application (docs/02 annuity rule).

There is no disbursement step yet (LF-020), so the schedule starts on the approval date: the
first instalment is due one month later, on the same day of the month (capped at the 28th).
No payments are recorded, so every instalment is shown as upcoming.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dates import add_months
from app.core.errors import Conflict
from app.models.application import Application, ApplicationStatus
from app.models.decision import Decision
from app.models.user import User
from app.schemas.schedule import InstalmentOut, ScheduleOut
from app.services import application_service, calculator_service


def approval_dates(db: Session, application_ids: list[uuid.UUID]) -> dict[uuid.UUID, date]:
    """The date of each application's standing approval (a correction is a later row)."""
    if not application_ids:
        return {}
    rows = db.execute(
        select(Decision.application_id, Decision.decided_at)
        .where(Decision.application_id.in_(application_ids), Decision.outcome == "approve")
        .order_by(Decision.seq)
    )
    return {application_id: decided_at.date() for application_id, decided_at in rows}


def due_date(start: date, number: int) -> date:
    return add_months(start, number)


def get_schedule(
    db: Session, *, user: User, application_id: uuid.UUID, now: datetime, ip: str | None
) -> ScheduleOut:
    application = application_service.get_for_user(
        db, user=user, application_id=application_id, now=now, ip=ip
    )
    return build(db, application)


def build(db: Session, application: Application) -> ScheduleOut:
    if application.status != ApplicationStatus.APPROVED.value:
        raise Conflict("Only an approved application has a repayment schedule")
    start = approval_dates(db, [application.id]).get(application.id)
    if start is None:  # cannot happen: APPROVED is only set by recording an approval
        raise Conflict("The approval date for this application is missing")
    amount = int(application.amount_vnd)
    rows = calculator_service.schedule(amount, application.term_months)
    quoted = calculator_service.quote(amount, application.term_months)
    total = sum(r.payment_vnd for r in rows)
    return ScheduleOut(
        application_id=application.id,
        start_date=start,
        annual_rate_percent=float(quoted.annual_rate * 100),
        term_months=application.term_months,
        monthly_payment_vnd=quoted.monthly_payment_vnd,
        total_paid_vnd=total,
        total_interest_vnd=total - amount,
        instalments=[
            InstalmentOut(
                number=r.number,
                due_date=due_date(start, r.number),
                payment_vnd=r.payment_vnd,
                principal_vnd=r.principal_vnd,
                interest_vnd=r.interest_vnd,
                balance_vnd=r.balance_vnd,
            )
            for r in rows
        ],
    )
