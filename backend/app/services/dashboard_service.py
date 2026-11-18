"""LF-019 operations dashboard (supervisors only, docs/01).

Definitions, so the numbers always agree:
- Applications by status: applications *created* in the range, counted by their status now.
- Decided: applications whose *first* approve/reject decision was recorded in the range. Their
  outcome is the standing one, so a supervisor's correction (BR-14) changes the outcome but not
  the time. Approval rate = approved / decided. Request-info and refer are not final.
- Average decision time: submission to that first final decision, in hours (never-submitted
  imported drafts have none).
- AI cost per application is not shown: the AI features are deferred (D-026).
"""

import uuid
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import UnprocessableEntity
from app.models.application import Application, ApplicationStatus
from app.models.decision import Decision
from app.models.user import User
from app.schemas.dashboard import DashboardOut, StatusCount
from app.services import audit_service, sla_service

MAX_RANGE_DAYS = 366
DEFAULT_RANGE_DAYS = 30
_FINAL = ("approve", "reject")
_STATUS_ORDER = (
    ApplicationStatus.DRAFT,
    ApplicationStatus.SUBMITTED,
    ApplicationStatus.IN_REVIEW,
    ApplicationStatus.NEEDS_INFO,
    ApplicationStatus.REFERRED,
    ApplicationStatus.APPROVED,
    ApplicationStatus.REJECTED,
)


def _bounds(start: date, end: date) -> tuple[datetime, datetime]:
    """Inclusive dates -> [start 00:00, day after end 00:00) in UTC."""
    return (
        datetime.combine(start, time.min, tzinfo=UTC),
        datetime.combine(end + timedelta(days=1), time.min, tzinfo=UTC),
    )


def summary(
    db: Session,
    *,
    viewer: User,
    date_from: date | None,
    date_to: date | None,
    now: datetime,
    ip: str | None,
) -> DashboardOut:
    end = date_to or now.date()
    start = date_from or end - timedelta(days=DEFAULT_RANGE_DAYS - 1)
    if (end - start).days + 1 > MAX_RANGE_DAYS:
        raise UnprocessableEntity(f"Choose a range of at most {MAX_RANGE_DAYS} days")
    low, high = _bounds(start, end)

    sla_service.sweep(db, now=now)  # so "overdue now" is current

    counts = {
        status: number
        for status, number in db.execute(
            select(Application.status, func.count())
            .where(Application.created_at >= low, Application.created_at < high)
            .group_by(Application.status)
        )
    }
    by_status = [StatusCount(status=s.value, count=counts.get(s.value, 0)) for s in _STATUS_ORDER]

    first_final = (
        select(
            Decision.application_id.label("application_id"),
            func.min(Decision.decided_at).label("first_at"),
        )
        .where(Decision.outcome.in_(_FINAL))
        .group_by(Decision.application_id)
        .subquery()
    )
    cohort = db.execute(
        select(first_final.c.application_id, first_final.c.first_at, Application.submitted_at)
        .join(Application, Application.id == first_final.c.application_id)
        .where(first_final.c.first_at >= low, first_final.c.first_at < high)
    ).all()
    outcome_of = _standing_outcomes(db, [row[0] for row in cohort])
    approved = sum(1 for row in cohort if outcome_of.get(row[0]) == "approve")
    rejected = sum(1 for row in cohort if outcome_of.get(row[0]) == "reject")
    waits = [
        (first_at - submitted).total_seconds() / 3600
        for _, first_at, submitted in cohort
        if submitted is not None
    ]

    overdue_now = (
        db.scalar(
            select(func.count())
            .select_from(Application)
            .where(
                Application.sla_breached_at.is_not(None),
                Application.status.in_(sla_service.WAITING_STATUSES),
            )
        )
        or 0
    )

    audit_service.record(
        db,
        action="dashboard.view",
        now=now,
        actor_id=viewer.id,
        target_type="dashboard",
        ip_address=ip,
    )
    db.commit()
    decided = approved + rejected
    return DashboardOut(
        date_from=start,
        date_to=end,
        total_applications=sum(counts.values()),
        by_status=by_status,
        decided=decided,
        approved=approved,
        rejected=rejected,
        approval_rate_percent=round(approved / decided * 100, 1) if decided else None,
        avg_decision_hours=round(sum(waits) / len(waits), 2) if waits else None,
        overdue_now=overdue_now,
    )


def _standing_outcomes(db: Session, application_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    """The latest approve/reject row per application (a correction is a later row)."""
    if not application_ids:
        return {}
    rows = db.execute(
        select(Decision.application_id, Decision.outcome)
        .where(Decision.application_id.in_(application_ids), Decision.outcome.in_(_FINAL))
        .order_by(Decision.seq)
    )
    return {application_id: outcome for application_id, outcome in rows}  # later rows win
