"""LF-017 SLA escalation (docs/04; BR-11, BR-15): a file waiting at a supervisor over the limit
becomes overdue, the supervisors are notified once, and the breach is logged."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.outbox import OutboxMessage
from app.models.user import Role
from app.services import sla_service

from .conftest import TEST_PASSWORD
from .test_lf010_queue import new_application, queued, upload_all

LIMIT = timedelta(hours=24)


@pytest.fixture
def supervisor(make_user):
    return make_user(Role.SUPERVISOR)


@pytest.fixture
def officer(make_user):
    return make_user(Role.OFFICER)


def refer(client, headers, app_id):
    response = client.post(
        f"/applications/{app_id}/decision", headers=headers, json={"outcome": "refer"}
    )
    assert response.status_code == 201
    return response


def referred(client, db, make_user, officer):
    app_id = queued(client, make_user, db)
    refer(client, officer[1], app_id)
    return app_id


def row(db, app_id):
    db.expire_all()
    return db.get(Application, uuid.UUID(app_id))


def breach_audits(db, app_id):
    return db.scalars(
        select(AuditLog).where(
            AuditLog.application_id == uuid.UUID(app_id), AuditLog.action == "sla.breached"
        )
    ).all()


def overdue_notices(db, app_id):
    return db.scalars(
        select(OutboxMessage).where(
            OutboxMessage.application_id == uuid.UUID(app_id),
            OutboxMessage.template == "sla_overdue",
        )
    ).all()


def queue(client, headers, **params):
    return client.get("/queue", headers=headers, params=params)


# --- the clock starts when the supervisor gets the file --------------------------------------


def test_lf017_referring_starts_the_supervisor_clock(
    client, db, clock, make_user, officer, supervisor
):
    started = clock()

    app_id = referred(client, db, make_user, officer)

    assert row(db, app_id).assigned_supervisor_at == started
    assert row(db, app_id).sla_breached_at is None


# --- AC: more than 24 h at a supervisor -> overdue, admin notified, breach logged ------------


def test_lf017_exactly_at_the_limit_is_not_overdue_but_just_after_is(
    client, db, clock, make_user, officer, supervisor
):
    app_id = referred(client, db, make_user, officer)

    clock.advance(hours=24)
    assert sla_service.sweep(db, now=clock()) == []
    assert row(db, app_id).sla_breached_at is None

    clock.advance(seconds=1)
    assert sla_service.sweep(db, now=clock()) == [uuid.UUID(app_id)]
    assert row(db, app_id).sla_breached_at == clock()


def test_lf017_breach_is_logged_once_and_every_active_supervisor_is_told_once(
    client, db, clock, make_user, officer, supervisor
):
    other = make_user(Role.SUPERVISOR)
    gone, _ = make_user(Role.SUPERVISOR, active=False)
    app_id = referred(client, db, make_user, officer)

    clock.advance(hours=25)
    sla_service.sweep(db, now=clock())
    sla_service.sweep(db, now=clock())  # running it again changes nothing

    assert len(breach_audits(db, app_id)) == 1
    assert breach_audits(db, app_id)[0].actor_id is None  # the system recorded it
    notices = overdue_notices(db, app_id)
    assert {n.recipient_user_id for n in notices} == {supervisor[0].id, other[0].id}
    assert gone.id not in {n.recipient_user_id for n in notices}
    assert len(notices) == 2


def test_lf017_notice_holds_a_link_and_no_personal_data(
    client, db, clock, make_user, officer, supervisor
):
    owner, _, app_id = new_application(client, make_user, name="Secret Name Person")
    upload_all(client, _headers_of(client, owner), app_id)
    refer(client, officer[1], app_id)

    clock.advance(hours=25)
    sla_service.sweep(db, now=clock())

    body = overdue_notices(db, app_id)[0].body
    assert f"/review/{app_id}" in body
    assert "Secret Name Person" not in body
    assert "VND" not in body


def _headers_of(client, user):
    token = client.post("/auth/login", json={"email": user.email, "password": TEST_PASSWORD})
    return {"Authorization": f"Bearer {token.json()['access_token']}"}


# --- overdue shows in the queue and the file view --------------------------------------------


def test_lf017_overdue_file_is_flagged_in_the_queue_and_the_file_view(
    client, db, clock, make_user, officer, supervisor
):
    app_id = referred(client, db, make_user, officer)
    clock.advance(hours=25)
    viewer = make_user(Role.SUPERVISOR)  # earlier tokens have expired with the clock

    listed = queue(client, viewer[1], status="REFERRED").json()
    detail = client.get(f"/applications/{app_id}/review", headers=viewer[1]).json()

    assert [i["id"] for i in listed["items"]] == [app_id]
    assert "overdue" in listed["items"][0]["flags"]
    assert "overdue" in detail["flags"]


def test_lf017_queue_can_be_filtered_to_overdue_files(
    client, db, clock, make_user, officer, supervisor
):
    late = referred(client, db, make_user, officer)
    clock.advance(hours=25)
    fresh = queued(client, make_user, db)  # in review, no supervisor, never overdue
    viewer = make_user(Role.SUPERVISOR)

    only_overdue = queue(client, viewer[1], status="REFERRED", flag="overdue").json()
    in_review = queue(client, viewer[1], status="IN_REVIEW", flag="overdue").json()

    assert [i["id"] for i in only_overdue["items"]] == [late]
    assert in_review["items"] == []
    assert fresh not in [i["id"] for i in only_overdue["items"]]


def test_lf017_reading_the_queue_is_enough_to_mark_and_announce(
    client, db, clock, make_user, officer, supervisor
):
    app_id = referred(client, db, make_user, officer)
    clock.advance(hours=25)
    viewer = make_user(Role.SUPERVISOR)

    queue(client, viewer[1], status="REFERRED")
    queue(client, viewer[1], status="REFERRED")

    assert row(db, app_id).sla_breached_at is not None
    assert len(breach_audits(db, app_id)) == 1


# --- negative cases --------------------------------------------------------------------------


def test_lf017_a_file_with_no_supervisor_never_becomes_overdue(
    client, db, clock, make_user, officer
):
    app_id = queued(client, make_user, db)

    clock.advance(days=10)

    assert sla_service.sweep(db, now=clock()) == []
    assert row(db, app_id).sla_breached_at is None


def test_lf017_a_file_decided_in_time_is_not_overdue(
    client, db, clock, make_user, officer, supervisor
):
    app_id = referred(client, db, make_user, officer)
    clock.advance(hours=23)
    approver = make_user(Role.SUPERVISOR)
    decided = client.post(
        f"/applications/{app_id}/decision", headers=approver[1], json={"outcome": "approve"}
    )
    assert decided.status_code == 201

    clock.advance(hours=5)

    assert sla_service.sweep(db, now=clock()) == []
    assert row(db, app_id).sla_breached_at is None


def test_lf017_flag_goes_away_once_the_file_is_decided_but_the_breach_stays_logged(
    client, db, clock, make_user, officer, supervisor
):
    app_id = referred(client, db, make_user, officer)
    clock.advance(hours=25)
    viewer = make_user(Role.SUPERVISOR)
    client.get(f"/applications/{app_id}/review", headers=viewer[1])  # marks it

    client.post(f"/applications/{app_id}/decision", headers=viewer[1], json={"outcome": "approve"})

    detail = client.get(f"/applications/{app_id}/review", headers=viewer[1]).json()
    assert "overdue" not in detail["flags"]
    assert len(breach_audits(db, app_id)) == 1


def test_lf017_overdue_never_changes_the_status_or_decides(
    client, db, clock, make_user, officer, supervisor
):
    app_id = referred(client, db, make_user, officer)

    clock.advance(days=5)
    sla_service.sweep(db, now=clock())

    assert row(db, app_id).status == "REFERRED"  # BR-15: only a person decides


def test_lf017_time_waiting_for_the_borrower_does_not_count(
    client, db, clock, make_user, officer, supervisor
):
    owner, borrower, app_id = new_application(client, make_user)
    upload_all(client, borrower, app_id)
    client.post(
        f"/applications/{app_id}/decision",
        headers=officer[1],
        json={"outcome": "refer"},
    )
    clock.advance(hours=2)
    asker = make_user(Role.SUPERVISOR)
    asked = client.post(
        f"/applications/{app_id}/decision",
        headers=asker[1],
        json={
            "outcome": "request_info",
            "explanation": "Please upload your latest bank statement.",
        },
    )
    assert asked.status_code == 201
    assert row(db, app_id).status == "NEEDS_INFO"

    clock.advance(hours=48)  # a long wait for the borrower
    assert sla_service.sweep(db, now=clock()) == []

    back = client.post(f"/applications/{app_id}/resubmit", headers=_headers_of(client, owner))
    assert back.status_code == 200
    assert row(db, app_id).assigned_supervisor_at == clock()  # clock restarted
    clock.advance(hours=23)
    assert sla_service.sweep(db, now=clock()) == []
    clock.advance(hours=2)
    assert sla_service.sweep(db, now=clock()) == [uuid.UUID(app_id)]


def test_lf017_limit_comes_from_settings(
    client, db, clock, make_user, officer, supervisor, monkeypatch
):
    monkeypatch.setattr(get_settings(), "supervisor_sla_hours", 1)
    app_id = referred(client, db, make_user, officer)

    clock.advance(minutes=61)

    assert sla_service.sweep(db, now=clock()) == [uuid.UUID(app_id)]


def test_lf017_only_supervisors_and_officers_can_read_the_referred_queue(
    client, db, make_user, officer
):
    _, borrower = make_user(Role.BORROWER)

    assert queue(client, borrower, status="REFERRED").status_code == 403
    assert queue(client, officer[1], status="REFERRED").status_code == 200
