"""LF-014 repayment schedule endpoint and reminder emails (docs/04)."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.dates import add_months
from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.outbox import OutboxMessage
from app.models.reminder_log import ReminderLog
from app.models.user import Role
from app.services import calculator_service, reminder_service

from .test_lf010_queue import new_application, upload_all


def approve(client, supervisor_headers, app_id):
    response = client.post(
        f"/applications/{app_id}/decision", headers=supervisor_headers, json={"outcome": "approve"}
    )
    assert response.status_code == 201, response.text


@pytest.fixture
def supervisor(make_user):
    return make_user(Role.SUPERVISOR)


@pytest.fixture
def approved(client, db, clock, make_user, supervisor):
    """(owner, borrower headers, application id, approval date) for an approved application."""
    owner, headers, app_id = new_application(client, make_user)
    upload_all(client, headers, app_id)
    approve(client, supervisor[1], app_id)
    return owner, headers, app_id, clock().date()


def loan(db, app_id):
    """(amount in VND, term in months) as stored; the shared helper picks them."""
    application = db.get(Application, uuid.UUID(app_id))
    return int(application.amount_vnd), application.term_months


def to_day(clock, target):
    """Move the fake clock to `target` (a date), keeping the time of day."""
    clock.advance(days=(target - clock().date()).days)


def notices(db, app_id):
    db.expire_all()
    return db.scalars(
        select(OutboxMessage)
        .where(OutboxMessage.application_id == uuid.UUID(app_id))
        .where(OutboxMessage.template.like("reminder_%"))
        .order_by(OutboxMessage.created_at, OutboxMessage.template)
    ).all()


# --- the schedule: due date, principal and interest ------------------------------------------


def test_lf014_schedule_lists_every_instalment_with_due_date_principal_and_interest(
    client, db, approved
):
    _, headers, app_id, start = approved
    amount, term = loan(db, app_id)

    response = client.get(f"/applications/{app_id}/schedule", headers=headers)

    assert response.status_code == 200
    body = response.json()
    rows = body["instalments"]
    assert body["start_date"] == start.isoformat()
    assert len(rows) == term == body["term_months"]
    assert rows[0]["due_date"] == add_months(start, 1).isoformat()
    assert rows[-1]["due_date"] == add_months(start, term).isoformat()
    expected = calculator_service.schedule(amount, term)
    assert [r["payment_vnd"] for r in rows] == [e.payment_vnd for e in expected]
    assert [r["interest_vnd"] for r in rows] == [e.interest_vnd for e in expected]
    assert rows[-1]["balance_vnd"] == 0
    assert sum(r["principal_vnd"] for r in rows) == amount
    assert body["total_interest_vnd"] == body["total_paid_vnd"] - amount
    assert body["monthly_payment_vnd"] == rows[0]["payment_vnd"]


def test_lf014_staff_can_read_a_schedule_too(client, make_user, approved):
    _, _, app_id, _ = approved
    officer = make_user(Role.OFFICER)
    supervisor = make_user(Role.SUPERVISOR)

    assert client.get(f"/applications/{app_id}/schedule", headers=officer[1]).status_code == 200
    assert client.get(f"/applications/{app_id}/schedule", headers=supervisor[1]).status_code == 200


def test_lf014_another_borrower_cannot_read_it(client, make_user, approved):
    _, _, app_id, _ = approved
    _, stranger = make_user(Role.BORROWER)

    assert client.get(f"/applications/{app_id}/schedule", headers=stranger).status_code == 403


def test_lf014_a_file_that_is_not_approved_has_no_schedule(client, db, make_user):
    _, headers, app_id = new_application(client, make_user)
    upload_all(client, headers, app_id)  # IN_REVIEW

    response = client.get(f"/applications/{app_id}/schedule", headers=headers)

    assert response.status_code == 409
    assert "approved" in response.json()["detail"]


def test_lf014_a_rejected_application_has_no_schedule(client, db, make_user, supervisor):
    _, headers, app_id = new_application(client, make_user)
    upload_all(client, headers, app_id)
    client.post(
        f"/applications/{app_id}/decision",
        headers=supervisor[1],
        json={
            "outcome": "reject",
            "reason_code": "INCOME_INSUFFICIENT",
            "explanation": "Your verified monthly income does not cover the new instalment.",
            "conditions": "Provide three more months of payslips showing a higher income.",
        },
    )

    assert client.get(f"/applications/{app_id}/schedule", headers=headers).status_code == 409


def test_lf014_unknown_application_and_missing_login(client, make_user):
    _, headers = make_user(Role.BORROWER)

    assert client.get(f"/applications/{uuid.uuid4()}/schedule", headers=headers).status_code == 404
    assert client.get(f"/applications/{uuid.uuid4()}/schedule").status_code == 401


# --- reminders: 7 days and 1 day before ------------------------------------------------------


def test_lf014_a_week_reminder_goes_out_seven_days_before_and_a_day_reminder_one_day_before(
    client, db, clock, approved
):
    owner, _, app_id, start = approved
    due = add_months(start, 1)

    to_day(clock, due - timedelta(days=8))
    assert reminder_service.send_due_reminders(db, now=clock()) == 0

    to_day(clock, due - timedelta(days=7))
    assert reminder_service.send_due_reminders(db, now=clock()) == 1
    to_day(clock, due - timedelta(days=1))
    assert reminder_service.send_due_reminders(db, now=clock()) == 1

    sent = notices(db, app_id)
    assert [m.template for m in sent] == ["reminder_week", "reminder_day"]
    assert {m.recipient_user_id for m in sent} == {owner.id}
    assert "within a week" in sent[0].body and "tomorrow" in sent[1].body


def test_lf014_the_reminder_names_the_instalment_and_date_but_no_amounts(
    client, db, clock, approved
):
    _, _, app_id, start = approved
    amount, term = loan(db, app_id)
    due = add_months(start, 1)
    to_day(clock, due - timedelta(days=7))

    reminder_service.send_due_reminders(db, now=clock())

    body = notices(db, app_id)[0].body
    assert f"Instalment 1 of {term}" in body
    assert f"{due:%d %B %Y}" in body
    assert f"/applications/{app_id}" in body
    assert "VND" not in body and f"{amount:,}" not in body


def test_lf014_running_again_the_same_day_sends_nothing_new(client, db, clock, approved):
    _, _, app_id, start = approved
    to_day(clock, add_months(start, 1) - timedelta(days=5))

    first = reminder_service.send_due_reminders(db, now=clock())
    second = reminder_service.send_due_reminders(db, now=clock())

    assert (first, second) == (1, 0)
    assert len(notices(db, app_id)) == 1
    assert len(db.scalars(select(ReminderLog)).all()) == 1


def test_lf014_a_late_run_sends_only_the_nearest_reminder(client, db, clock, approved):
    _, _, app_id, start = approved
    to_day(clock, add_months(start, 1) - timedelta(days=1))  # the first run is a day before

    assert reminder_service.send_due_reminders(db, now=clock()) == 1

    assert [m.template for m in notices(db, app_id)] == ["reminder_day"]


def test_lf014_nothing_is_sent_on_or_after_the_due_date(client, db, clock, approved):
    _, _, app_id, start = approved
    due = add_months(start, 1)

    to_day(clock, due)
    assert reminder_service.send_due_reminders(db, now=clock()) == 0
    to_day(clock, due + timedelta(days=2))
    # day 2 after the first due date is still 25+ days before the second one
    assert reminder_service.send_due_reminders(db, now=clock()) == 0
    assert notices(db, app_id) == []


def test_lf014_each_later_instalment_gets_its_own_reminders(client, db, clock, approved):
    _, _, app_id, start = approved
    _, term = loan(db, app_id)
    to_day(clock, add_months(start, 3) - timedelta(days=7))

    assert reminder_service.send_due_reminders(db, now=clock()) == 1

    assert f"Instalment 3 of {term}" in notices(db, app_id)[0].body


def test_lf014_nothing_is_sent_for_a_file_that_is_not_approved(client, db, clock, make_user):
    _, headers, app_id = new_application(client, make_user)
    upload_all(client, headers, app_id)  # IN_REVIEW
    clock.advance(days=40)

    assert reminder_service.send_due_reminders(db, now=clock()) == 0


def test_lf014_queued_reminders_are_audited(client, db, clock, approved):
    _, _, app_id, start = approved
    to_day(clock, add_months(start, 1) - timedelta(days=4))

    reminder_service.send_due_reminders(db, now=clock())

    queued = db.scalars(
        select(AuditLog).where(
            AuditLog.application_id == uuid.UUID(app_id),
            AuditLog.action == "notification.queued",
        )
    ).all()
    assert len(queued) >= 2  # the approval email and the reminder


# --- opt-out in settings ---------------------------------------------------------------------


def test_lf014_reminders_are_on_by_default_and_can_be_switched_off_and_on(client, db, make_user):
    owner, headers = make_user(Role.BORROWER)

    assert client.get("/me/settings", headers=headers).json() == {"repayment_reminders": True}
    off = client.put("/me/settings", headers=headers, json={"repayment_reminders": False})
    assert off.json() == {"repayment_reminders": False}
    assert client.get("/me/settings", headers=headers).json()["repayment_reminders"] is False
    client.put("/me/settings", headers=headers, json={"repayment_reminders": True})

    actions = db.scalars(
        select(AuditLog.action).where(AuditLog.actor_id == owner.id).order_by(AuditLog.seq)
    ).all()
    assert [a for a in actions if a.startswith("settings.")] == [
        "settings.reminders_off",
        "settings.reminders_on",
    ]


def test_lf014_a_borrower_who_opted_out_gets_no_reminders_until_they_opt_back_in(
    client, db, clock, approved
):
    owner, headers, app_id, start = approved
    client.put("/me/settings", headers=headers, json={"repayment_reminders": False})
    to_day(clock, add_months(start, 1) - timedelta(days=6))

    assert reminder_service.send_due_reminders(db, now=clock()) == 0
    assert notices(db, app_id) == []

    owner.repayment_reminders = True
    db.commit()
    assert reminder_service.send_due_reminders(db, now=clock()) == 1


def test_lf014_an_inactive_account_gets_no_reminders(client, db, clock, approved):
    owner, _, app_id, start = approved
    owner.is_active = False
    db.commit()
    to_day(clock, add_months(start, 1) - timedelta(days=6))

    assert reminder_service.send_due_reminders(db, now=clock()) == 0
    assert notices(db, app_id) == []


def test_lf014_only_borrowers_have_these_settings(client, make_user):
    officer = make_user(Role.OFFICER)

    assert client.get("/me/settings", headers=officer[1]).status_code == 403
    assert (
        client.put(
            "/me/settings", headers=officer[1], json={"repayment_reminders": False}
        ).status_code
        == 403
    )
    assert client.get("/me/settings").status_code == 401


# --- the supervisor's "send due reminders" ----------------------------------------------------


def test_lf014_a_supervisor_can_run_the_reminders_and_it_is_audited(
    client, db, clock, make_user, approved
):
    _, _, app_id, start = approved
    to_day(clock, add_months(start, 1) - timedelta(days=6))
    boss = make_user(Role.SUPERVISOR)  # logs in after the clock jump: tokens last 15 minutes

    first = client.post("/reminders/run", headers=boss[1])
    second = client.post("/reminders/run", headers=boss[1])

    assert first.status_code == 200 and first.json() == {"queued": 1}
    assert second.json() == {"queued": 0}
    assert len(notices(db, app_id)) == 1
    actions = db.scalars(select(AuditLog.action).where(AuditLog.actor_id == boss[0].id)).all()
    assert actions.count("reminders.run") == 2


@pytest.mark.parametrize("role", [Role.OFFICER, Role.BORROWER])
def test_lf014_only_a_supervisor_can_run_the_reminders(client, make_user, role):
    _, headers = make_user(role)

    assert client.post("/reminders/run", headers=headers).status_code == 403
    assert client.post("/reminders/run").status_code == 401


def test_lf014_app_row_untouched_by_reminders(client, db, clock, approved):
    _, _, app_id, start = approved
    to_day(clock, add_months(start, 1) - timedelta(days=3))

    reminder_service.send_due_reminders(db, now=clock())

    db.expire_all()
    assert db.get(Application, uuid.UUID(app_id)).status == "APPROVED"
