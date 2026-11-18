"""LF-008 Mock CIC check with progress (docs/04; BR-08, BR-15, C-10)."""

import uuid

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.user import Role
from app.services import cic_service
from app.services.cic_service import MockOutcome

from .test_lf010_queue import new_application, queued


def url(app_id):
    return f"/applications/{app_id}/cic-check"


@pytest.fixture
def officer(make_user):
    return make_user(Role.OFFICER)


@pytest.fixture
def outcome(monkeypatch):
    """Pick the synthetic bureau result instead of deriving it from the application id."""

    def _set(debt_group=1, *, times_out=False):
        monkeypatch.setattr(
            cic_service, "mock_outcome", lambda _id: MockOutcome(debt_group, times_out)
        )

    _set()
    return _set


def actions(db, app_id):
    return [
        a
        for a in db.scalars(
            select(AuditLog.action)
            .where(AuditLog.application_id == uuid.UUID(app_id))
            .order_by(AuditLog.seq)
        )
        if a.startswith("cic.")
    ]


# --- AC1: progress and time remaining while it runs ------------------------------------------


def test_lf008_running_check_shows_progress_and_seconds_remaining(
    client, db, clock, make_user, officer, outcome
):
    app_id = queued(client, make_user, db)

    started = client.post(url(app_id), headers=officer[1])
    assert started.status_code == 201
    assert started.json()["status"] == "running"
    assert started.json()["progress_pct"] == 0
    assert started.json()["seconds_remaining"] == get_settings().cic_duration_seconds

    clock.advance(seconds=10)
    body = client.get(url(app_id), headers=officer[1]).json()
    assert body["status"] == "running"
    assert body["progress_pct"] == 50
    assert body["seconds_remaining"] == get_settings().cic_duration_seconds - 10
    assert body["debt_group"] is None


def test_lf008_no_check_started_returns_null(client, db, make_user, officer):
    app_id = queued(client, make_user, db)

    response = client.get(url(app_id), headers=officer[1])

    assert response.status_code == 200
    assert response.json() is None


# --- AC2: result with debt group and summary -------------------------------------------------


@pytest.mark.parametrize(
    ("group", "flag"),
    [(1, "pass"), (2, "attention"), (3, "recommend_reject"), (5, "recommend_reject")],
)
def test_lf008_completed_check_shows_debt_group_and_flag(
    client, db, clock, make_user, officer, outcome, group, flag
):
    outcome(group)
    app_id = queued(client, make_user, db)
    client.post(url(app_id), headers=officer[1])

    clock.advance(seconds=get_settings().cic_duration_seconds)
    body = client.get(url(app_id), headers=officer[1]).json()

    assert body["status"] == "done"
    assert body["progress_pct"] == 100
    assert body["debt_group"] == group
    assert body["flag"] == flag
    assert f"Group {group}" in body["summary"]
    assert actions(db, app_id) == ["cic.started", "cic.completed"]


def test_lf008_bad_debt_group_never_changes_the_application(
    client, db, clock, make_user, officer, outcome
):
    outcome(5)
    app_id = queued(client, make_user, db)
    client.post(url(app_id), headers=officer[1])
    clock.advance(seconds=get_settings().cic_duration_seconds)
    client.get(url(app_id), headers=officer[1])

    db.expire_all()
    application = db.get(Application, uuid.UUID(app_id))
    # BR-15: a recommend-reject flag is only shown; the status stays for a human to decide
    assert application.status == "IN_REVIEW"


# --- AC3: timeout, saved file, automatic retry -----------------------------------------------


def test_lf008_timeout_retries_automatically_then_completes(
    client, db, clock, make_user, officer, outcome
):
    outcome(2, times_out=True)
    app_id = queued(client, make_user, db)
    client.post(url(app_id), headers=officer[1])

    clock.advance(seconds=get_settings().cic_duration_seconds)
    stalled = client.get(url(app_id), headers=officer[1]).json()
    assert stalled["status"] == "running"  # the bureau is silent
    assert stalled["progress_pct"] == 90
    assert stalled["seconds_remaining"] is None

    clock.advance(seconds=get_settings().cic_attempt_timeout_seconds)
    retrying = client.get(url(app_id), headers=officer[1]).json()
    assert retrying["status"] == "running"
    assert retrying["attempt"] == 2
    assert "retrying automatically" in retrying["message"]
    assert retrying["progress_pct"] == 0

    clock.advance(seconds=get_settings().cic_duration_seconds)
    done = client.get(url(app_id), headers=officer[1]).json()
    assert done["status"] == "done"
    assert done["debt_group"] == 2
    assert actions(db, app_id) == ["cic.started", "cic.timeout", "cic.completed"]
    db.expire_all()
    assert db.get(Application, uuid.UUID(app_id)).status == "IN_REVIEW"  # file stays saved


def test_lf008_gives_up_after_the_last_attempt_and_can_be_started_again(
    client, db, clock, make_user, officer, outcome, monkeypatch
):
    outcome(1, times_out=True)
    monkeypatch.setattr(get_settings(), "cic_max_attempts", 1)
    app_id = queued(client, make_user, db)
    client.post(url(app_id), headers=officer[1])

    clock.advance(seconds=get_settings().cic_attempt_timeout_seconds)
    body = client.get(url(app_id), headers=officer[1]).json()
    assert body["status"] == "timeout"
    assert "did not respond after 1 attempts" in body["message"]
    assert body["debt_group"] is None

    outcome(1)
    again = client.post(url(app_id), headers=officer[1])
    assert again.status_code == 201
    assert again.json()["status"] == "running"
    assert again.json()["attempt"] == 1


# --- negative cases --------------------------------------------------------------------------


def test_lf008_second_start_while_running_is_refused(client, db, make_user, officer, outcome):
    app_id = queued(client, make_user, db)
    client.post(url(app_id), headers=officer[1])

    response = client.post(url(app_id), headers=officer[1])

    assert response.status_code == 409
    assert "already running" in response.json()["detail"]


def test_lf008_start_after_completion_is_refused(client, db, clock, make_user, officer, outcome):
    app_id = queued(client, make_user, db)
    client.post(url(app_id), headers=officer[1])
    clock.advance(seconds=get_settings().cic_duration_seconds)

    response = client.post(url(app_id), headers=officer[1])

    assert response.status_code == 409
    assert "already complete" in response.json()["detail"]


def test_lf008_file_not_in_review_is_refused(client, db, make_user, officer):
    _, _, app_id = new_application(client, make_user)  # SUBMITTED: documents still missing

    response = client.post(url(app_id), headers=officer[1])

    assert response.status_code == 409
    assert "in review" in response.json()["detail"]


def test_lf008_borrower_is_forbidden_and_the_refusal_is_audited(client, db, make_user):
    owner, headers, app_id = new_application(client, make_user)

    assert client.post(url(app_id), headers=headers).status_code == 403
    assert client.get(url(app_id), headers=headers).status_code == 403
    denied = db.scalars(
        select(AuditLog).where(AuditLog.actor_id == owner.id, AuditLog.action == "access.denied")
    ).all()
    assert len(denied) == 2


def test_lf008_requires_login(client, db, make_user):
    app_id = queued(client, make_user, db)

    assert client.post(url(app_id)).status_code == 401
    assert client.get(url(app_id)).status_code == 401


def test_lf008_unknown_application_is_404(client, officer):
    assert client.post(url(uuid.uuid4()), headers=officer[1]).status_code == 404
    assert client.get(url(uuid.uuid4()), headers=officer[1]).status_code == 404


def test_lf008_another_officers_file_is_forbidden(client, db, make_user, officer, outcome):
    app_id = queued(client, make_user, db)
    client.post(f"/applications/{app_id}/claim", headers=officer[1])
    other = make_user(Role.OFFICER)

    assert client.post(url(app_id), headers=other[1]).status_code == 403
    assert client.get(url(app_id), headers=other[1]).status_code == 403


def test_lf008_supervisor_can_run_a_check(client, db, make_user, outcome):
    app_id = queued(client, make_user, db)
    supervisor = make_user(Role.SUPERVISOR)

    assert client.post(url(app_id), headers=supervisor[1]).status_code == 201


# --- the mock itself -------------------------------------------------------------------------


def test_lf008_mock_outcome_is_deterministic_and_in_range():
    ids = [uuid.uuid4() for _ in range(200)]

    results = [cic_service.mock_outcome(i) for i in ids]

    assert results == [cic_service.mock_outcome(i) for i in ids]
    assert {r.debt_group for r in results} == {1, 2, 3, 4, 5}
    assert any(r.first_attempt_times_out for r in results)
    assert not all(r.first_attempt_times_out for r in results)


def test_lf008_flag_mapping_follows_br08():
    assert [cic_service.flag_for(g) for g in range(1, 6)] == [
        "pass",
        "attention",
        "recommend_reject",
        "recommend_reject",
        "recommend_reject",
    ]
