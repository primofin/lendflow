"""LF-008 mock CIC check (BR-08, C-10). Synthetic and deterministic; the clock drives progress.

There is no background worker: the check's state is worked out from the stored start time each
time it is read, so progress survives a restart and tests can move the clock. The outcome comes
from the application id only, never from personal data. The result is a flag for the officer;
no code here changes an application's status (BR-15).
"""

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import Conflict
from app.models.application import Application, ApplicationStatus
from app.models.cic_check import CicCheck
from app.models.user import User
from app.schemas.cic import CicCheckOut, CicFlag
from app.services import application_service, audit_service

_GROUP_TABLE = (1, 1, 1, 1, 1, 2, 2, 3, 4, 5)  # synthetic spread of debt groups

_SUMMARIES = {
    1: "Group 1: standard debt, no overdue payments (synthetic data).",
    2: "Group 2: debt needing attention, past due 10 to 90 days (synthetic data).",
    3: "Group 3: substandard debt, past due 91 to 180 days (synthetic data).",
    4: "Group 4: doubtful debt, past due 181 to 360 days (synthetic data).",
    5: "Group 5: loss-risk debt, past due over 360 days (synthetic data).",
}


@dataclass(frozen=True)
class MockOutcome:
    debt_group: int
    first_attempt_times_out: bool


def mock_outcome(application_id: uuid.UUID) -> MockOutcome:
    """Same application, same result. About one file in four times out on the first try."""
    digest = int.from_bytes(hashlib.sha256(application_id.bytes).digest()[:8], "big")
    return MockOutcome(
        debt_group=_GROUP_TABLE[digest % len(_GROUP_TABLE)],
        first_attempt_times_out=(digest // 10) % 4 == 0,
    )


def flag_for(debt_group: int) -> CicFlag:
    if debt_group == 1:
        return "pass"
    return "attention" if debt_group == 2 else "recommend_reject"


def _latest(db: Session, application_id: uuid.UUID, *, lock: bool = False) -> CicCheck | None:
    statement = (
        select(CicCheck)
        .where(CicCheck.application_id == application_id)
        .order_by(CicCheck.started_at.desc())
        .limit(1)
    )
    if lock:
        statement = statement.with_for_update()
    return db.scalars(statement).first()


def start(
    db: Session, *, user: User, application_id: uuid.UUID, now: datetime, ip: str | None
) -> CicCheckOut:
    application = application_service.get_for_user(
        db, user=user, application_id=application_id, now=now, ip=ip, audit_read=False
    )
    if application.status != ApplicationStatus.IN_REVIEW.value:
        raise Conflict("The credit check can only run on a file that is in review")
    existing = _latest(db, application.id, lock=True)
    if existing is not None:
        _advance(db, existing, application, now)
        if existing.status == "running":
            raise Conflict("A credit check is already running for this application")
        if existing.status == "done":
            raise Conflict("The credit check for this application is already complete")
    check = CicCheck(
        application_id=application.id,
        started_by=user.id,
        status="running",
        attempt=1,
        started_at=now,
        attempt_started_at=now,
    )
    db.add(check)
    audit_service.record(
        db,
        action="cic.started",
        now=now,
        actor_id=user.id,
        target_type="application",
        target_id=application.id,
        application_id=application.id,
        ip_address=ip,
    )
    db.commit()
    return _out(check, application, now)


def get_latest(
    db: Session, *, user: User, application_id: uuid.UUID, now: datetime, ip: str | None
) -> CicCheckOut | None:
    application = application_service.get_for_user(
        db, user=user, application_id=application_id, now=now, ip=ip, audit_read=False
    )
    check = _latest(db, application.id, lock=True)
    if check is None:
        return None
    _advance(db, check, application, now)
    db.commit()
    return _out(check, application, now)


def _advance(db: Session, check: CicCheck, application: Application, now: datetime) -> None:
    """Move a running check forward: finish it, or time the attempt out and retry (AC3)."""
    if check.status != "running":
        return
    settings = get_settings()
    outcome = mock_outcome(application.id)
    elapsed = (now - check.attempt_started_at).total_seconds()
    will_time_out = outcome.first_attempt_times_out and check.attempt == 1

    if not will_time_out:
        if elapsed >= settings.cic_duration_seconds:
            check.status = "done"
            check.debt_group = outcome.debt_group
            check.finished_at = now
            _audit(db, check, "cic.completed", now)
        return

    if elapsed < settings.cic_attempt_timeout_seconds:
        return
    _audit(db, check, "cic.timeout", now)
    if check.attempt >= settings.cic_max_attempts:
        check.status = "timeout"
        check.finished_at = now
        return
    check.attempt += 1
    check.attempt_started_at = now


def _audit(db: Session, check: CicCheck, action: str, now: datetime) -> None:
    audit_service.record(
        db,
        action=action,
        now=now,
        actor_id=check.started_by,
        target_type="application",
        target_id=check.application_id,
        application_id=check.application_id,
    )


def _out(check: CicCheck, application: Application, now: datetime) -> CicCheckOut:
    settings = get_settings()
    max_attempts = settings.cic_max_attempts
    common = {
        "attempt": check.attempt,
        "max_attempts": max_attempts,
        "started_at": check.started_at,
        "finished_at": check.finished_at,
    }
    if check.status == "done" and check.debt_group is not None:
        return CicCheckOut(
            status="done",
            progress_pct=100,
            seconds_remaining=0,
            message="Credit check complete",
            debt_group=check.debt_group,
            flag=flag_for(check.debt_group),
            summary=_SUMMARIES[check.debt_group],
            **common,
        )
    if check.status == "timeout":
        return CicCheckOut(
            status="timeout",
            progress_pct=0,
            seconds_remaining=None,
            message=(
                f"The credit bureau did not respond after {max_attempts} attempts. "
                "The file is saved; start the check again later."
            ),
            debt_group=None,
            flag=None,
            summary=None,
            **common,
        )
    elapsed = max((now - check.attempt_started_at).total_seconds(), 0)
    stalls = mock_outcome(application.id).first_attempt_times_out and check.attempt == 1
    pct = min(int(elapsed / settings.cic_duration_seconds * 100), 90 if stalls else 99)
    left = max(settings.cic_duration_seconds - int(elapsed), 0)
    remaining = None if stalls and pct >= 90 else left
    retry_note = (
        ""
        if check.attempt == 1
        else (
            "The credit bureau did not respond in time. The file is saved and the check is "
            f"retrying automatically (attempt {check.attempt} of {max_attempts}). "
        )
    )
    return CicCheckOut(
        status="running",
        progress_pct=pct,
        seconds_remaining=remaining,
        message=retry_note + "Credit check in progress. You can keep using other screens.",
        debt_group=None,
        flag=None,
        summary=None,
        **common,
    )
