"""LF-019 Operations dashboard (docs/04; docs/01: supervisors only)."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.user import Role

from .test_lf010_queue import queued

URL = "/dashboard"
EXPLANATION = "Your verified monthly income does not cover the new instalment."
REJECT = {
    "outcome": "reject",
    "reason_code": "INCOME_INSUFFICIENT",
    "explanation": EXPLANATION,
    "conditions": "Provide three more months of payslips showing a higher income.",
}


@pytest.fixture
def supervisor(make_user):
    return make_user(Role.SUPERVISOR)


def get(client, headers, **params):
    return client.get(URL, headers=headers, params=params)


def submitted_now(db, clock, app_id):
    """The fake clock, not the database clock, is what decision times are measured against."""
    db.get(Application, uuid.UUID(app_id)).submitted_at = clock()
    db.commit()


def decide(client, headers, app_id, body):
    response = client.post(f"/applications/{app_id}/decision", headers=headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def counts(body):
    return {row["status"]: row["count"] for row in body["by_status"]}


# --- access -----------------------------------------------------------------------------------


@pytest.mark.parametrize("role", [Role.OFFICER, Role.BORROWER])
def test_lf019_only_a_supervisor_can_open_the_dashboard(client, db, make_user, role):
    user, headers = make_user(role)

    assert get(client, headers).status_code == 403
    denied = db.scalars(
        select(AuditLog).where(AuditLog.actor_id == user.id, AuditLog.action == "access.denied")
    ).all()
    assert len(denied) == 1


def test_lf019_requires_login(client):
    assert client.get(URL).status_code == 401


def test_lf019_opening_it_is_audited(client, db, supervisor):
    get(client, supervisor[1])

    actions = db.scalars(select(AuditLog.action).where(AuditLog.actor_id == supervisor[0].id)).all()
    assert "dashboard.view" in actions


# --- applications by status -------------------------------------------------------------------


def test_lf019_empty_system_shows_zeros_and_no_rates(client, supervisor):
    body = get(client, supervisor[1]).json()

    assert body["total_applications"] == 0
    assert [row["status"] for row in body["by_status"]] == [
        "DRAFT",
        "SUBMITTED",
        "IN_REVIEW",
        "NEEDS_INFO",
        "REFERRED",
        "APPROVED",
        "REJECTED",
    ]
    assert {row["count"] for row in body["by_status"]} == {0}
    assert body["decided"] == 0
    assert body["approval_rate_percent"] is None
    assert body["avg_decision_hours"] is None
    assert body["overdue_now"] == 0


def test_lf019_counts_applications_by_their_current_status(client, db, make_user, supervisor):
    queued(client, make_user, db)
    queued(client, make_user, db)
    approved = queued(client, make_user, db)
    decide(client, supervisor[1], approved, {"outcome": "approve"})

    body = get(client, supervisor[1]).json()

    assert counts(body)["IN_REVIEW"] == 2
    assert counts(body)["APPROVED"] == 1
    assert body["total_applications"] == 3


def test_lf019_only_applications_created_in_the_range_are_counted(
    client, db, make_user, supervisor
):
    old = queued(client, make_user, db)
    queued(client, make_user, db)
    db.get(Application, uuid.UUID(old)).created_at -= timedelta(days=90)
    db.commit()

    last_30 = get(client, supervisor[1]).json()
    older = get(
        client,
        supervisor[1],
        **{
            "from": (
                db.get(Application, uuid.UUID(old)).created_at.date() - timedelta(days=1)
            ).isoformat(),
            "to": (db.get(Application, uuid.UUID(old)).created_at.date()).isoformat(),
        },
    ).json()

    assert last_30["total_applications"] == 1
    assert older["total_applications"] == 1 and counts(older)["IN_REVIEW"] == 1


# --- decisions: approval rate and average decision time ---------------------------------------


def test_lf019_approval_rate_and_average_decision_time(client, db, clock, make_user, supervisor):
    first = queued(client, make_user, db)
    second = queued(client, make_user, db)
    submitted_now(db, clock, first)
    submitted_now(db, clock, second)

    clock.advance(hours=2)
    approver = make_user(Role.SUPERVISOR)  # tokens last 15 minutes, so log in after the jump
    decide(client, approver[1], first, {"outcome": "approve"})
    clock.advance(hours=2)
    rejecter = make_user(Role.SUPERVISOR)
    decide(client, rejecter[1], second, REJECT)

    body = get(client, make_user(Role.SUPERVISOR)[1]).json()

    assert (body["decided"], body["approved"], body["rejected"]) == (2, 1, 1)
    assert body["approval_rate_percent"] == 50.0
    assert body["avg_decision_hours"] == 3.0  # (2 h + 4 h) / 2


def test_lf019_request_info_and_refer_are_not_final_decisions(client, db, make_user, supervisor):
    asked = queued(client, make_user, db)
    referred = queued(client, make_user, db)
    officer = make_user(Role.OFFICER)
    decide(
        client,
        officer[1],
        asked,
        {"outcome": "request_info", "explanation": "Please upload your latest bank statement."},
    )
    decide(client, officer[1], referred, {"outcome": "refer"})

    body = get(client, supervisor[1]).json()

    assert body["decided"] == 0
    assert body["approval_rate_percent"] is None


def test_lf019_a_correction_changes_the_outcome_but_not_the_decision_time(
    client, db, clock, make_user, supervisor
):
    app_id = queued(client, make_user, db)
    submitted_now(db, clock, app_id)
    clock.advance(hours=1)
    rejecter = make_user(Role.SUPERVISOR)
    rejected = decide(client, rejecter[1], app_id, REJECT)
    clock.advance(hours=5)
    corrector = make_user(Role.SUPERVISOR)
    decide(
        client,
        corrector[1],
        app_id,
        {"outcome": "approve", "supersedes_id": rejected["id"]},
    )

    body = get(client, make_user(Role.SUPERVISOR)[1]).json()

    assert (body["decided"], body["approved"], body["rejected"]) == (1, 1, 0)
    assert body["approval_rate_percent"] == 100.0
    assert body["avg_decision_hours"] == 1.0


def test_lf019_decisions_outside_the_range_are_left_out(client, db, make_user, supervisor):
    app_id = queued(client, make_user, db)
    decide(client, supervisor[1], app_id, {"outcome": "approve"})

    far_past = get(client, supervisor[1], **{"from": "2020-01-01", "to": "2020-01-31"}).json()

    assert far_past["decided"] == 0
    assert far_past["approval_rate_percent"] is None
    assert get(client, supervisor[1]).json()["decided"] == 1


def test_lf019_the_end_date_is_inclusive(client, db, clock, make_user, supervisor):
    app_id = queued(client, make_user, db)
    decide(client, supervisor[1], app_id, {"outcome": "approve"})
    today = clock().date().isoformat()

    body = get(client, supervisor[1], **{"from": today, "to": today}).json()

    assert body["decided"] == 1
    assert (body["date_from"], body["date_to"]) == (today, today)


# --- overdue ----------------------------------------------------------------------------------


def test_lf019_counts_files_that_are_overdue_at_a_supervisor_now(
    client, db, clock, make_user, supervisor
):
    app_id = queued(client, make_user, db)
    officer = make_user(Role.OFFICER)
    decide(client, officer[1], app_id, {"outcome": "refer"})

    clock.advance(hours=25)

    assert get(client, make_user(Role.SUPERVISOR)[1]).json()["overdue_now"] == 1


# --- range rules ------------------------------------------------------------------------------


def test_lf019_defaults_to_the_last_thirty_days(client, clock, supervisor):
    body = get(client, supervisor[1]).json()

    assert body["date_to"] == clock().date().isoformat()
    assert body["date_from"] == (clock().date() - timedelta(days=29)).isoformat()


@pytest.mark.parametrize(
    ("params", "fragment"),
    [
        ({"from": "2026-02-01", "to": "2026-01-01"}, "must not be after"),
        ({"from": "2024-01-01", "to": "2026-01-01"}, "at most 366 days"),
        ({"from": "not-a-date"}, "date"),
    ],
)
def test_lf019_bad_ranges_are_refused_specifically(client, supervisor, params, fragment):
    response = get(client, supervisor[1], **params)

    assert response.status_code == 422
    assert fragment in str(response.json())
