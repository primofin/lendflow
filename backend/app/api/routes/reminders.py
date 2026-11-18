"""LF-014 repayment reminders: a borrower's opt-out, and a supervisor's "send due reminders"."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import BorrowerAuth, ClientIp, DbSession, Now, SupervisorAuth
from app.schemas.schedule import ReminderSettings
from app.services import audit_service, reminder_service

router = APIRouter(tags=["reminders"])


class ReminderRunOut(BaseModel):
    queued: int


@router.get("/me/settings")
def get_settings_for_me(auth: BorrowerAuth) -> ReminderSettings:
    """LF-014: whether repayment reminder emails are on (they are by default)."""
    return ReminderSettings(repayment_reminders=auth.user.repayment_reminders)


@router.put("/me/settings")
def update_settings(
    body: ReminderSettings, auth: BorrowerAuth, db: DbSession, clock: Now, ip: ClientIp
) -> ReminderSettings:
    """LF-014: opt in or out of repayment reminders."""
    auth.user.repayment_reminders = body.repayment_reminders
    audit_service.record(
        db,
        action="settings.reminders_on" if body.repayment_reminders else "settings.reminders_off",
        now=clock(),
        actor_id=auth.user.id,
        target_type="user",
        target_id=auth.user.id,
        ip_address=ip,
    )
    db.commit()
    return ReminderSettings(repayment_reminders=auth.user.repayment_reminders)


@router.post("/reminders/run")
def run_reminders(auth: SupervisorAuth, db: DbSession, clock: Now, ip: ClientIp) -> ReminderRunOut:
    """LF-014: queue every reminder that is due and not yet sent (safe to run repeatedly)."""
    queued = reminder_service.send_due_reminders(db, now=clock())
    audit_service.record(
        db,
        action="reminders.run",
        now=clock(),
        actor_id=auth.user.id,
        target_type="reminders",
        ip_address=ip,
    )
    db.commit()
    return ReminderRunOut(queued=queued)
