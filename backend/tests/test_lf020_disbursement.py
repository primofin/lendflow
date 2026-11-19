"""LF-020 disbursement with a simulated face match above 10M VND (C-07)."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.disbursement import Disbursement, DisbursementImmutable
from app.models.user import Role

from .test_lf010_queue import new_application, upload_all


@pytest.fixture
def supervisor(make_user):
    return make_user(Role.SUPERVISOR)


@pytest.fixture
def officer(make_user):
    return make_user(Role.OFFICER)


def approved(client, db, make_user, supervisor, amount):
    _, headers, app_id = new_application(client, make_user)
    upload_all(client, headers, app_id)
    db.get(Application, uuid.UUID(app_id)).amount_vnd = Decimal(amount)
    db.commit()
    response = client.post(
        f"/applications/{app_id}/decision", headers=supervisor[1], json={"outcome": "approve"}
    )
    assert response.status_code == 201, response.text
    return headers, app_id


def face_match(client, headers, app_id, result="pass"):
    return client.post(
        f"/applications/{app_id}/face-match", headers=headers, json={"result": result}
    )


def disburse(client, headers, app_id, match_id=None):
    return client.post(
        f"/applications/{app_id}/disbursement", headers=headers, json={"face_match_id": match_id}
    )


def actions(db, app_id):
    db.expire_all()
    return [
        a.action
        for a in db.scalars(
            select(AuditLog)
            .where(AuditLog.application_id == uuid.UUID(app_id))
            .order_by(AuditLog.seq)
        )
    ]


def test_lf020_over_threshold_without_face_match_is_blocked_and_logged(
    client, db, make_user, supervisor, officer
):
    _, app_id = approved(client, db, make_user, supervisor, 12_000_000)

    response = disburse(client, officer[1], app_id)

    assert response.status_code == 403
    assert "face match" in response.json()["detail"]
    assert "disbursement.blocked" in actions(db, app_id)
    assert db.scalar(select(Disbursement)) is None


def test_lf020_failed_face_match_blocks_and_is_logged_then_retry_passes(
    client, db, make_user, supervisor, officer
):
    _, app_id = approved(client, db, make_user, supervisor, 12_000_000)
    failed = face_match(client, officer[1], app_id, "fail")
    assert failed.status_code == 201 and failed.json()["passed"] is False

    blocked = disburse(client, officer[1], app_id, failed.json()["id"])

    assert blocked.status_code == 403
    log = actions(db, app_id)
    assert "face_match.failed" in log and "disbursement.blocked" in log

    good = face_match(client, officer[1], app_id, "pass")
    ok = disburse(client, officer[1], app_id, good.json()["id"])
    assert ok.status_code == 201
    assert ok.json()["amount_vnd"] == 12_000_000
    assert ok.json()["face_match_id"] == good.json()["id"]
    assert "disbursement.created" in actions(db, app_id)


def test_lf020_at_or_below_threshold_needs_no_face_match(
    client, db, make_user, supervisor, officer
):
    _, app_id = approved(client, db, make_user, supervisor, 5_000_000)
    assert (
        client.get(f"/applications/{app_id}/disbursement", headers=officer[1]).json()[
            "face_match_required"
        ]
        is False
    )

    response = disburse(client, officer[1], app_id)

    assert response.status_code == 201
    assert response.json()["face_match_id"] is None


def test_lf020_exactly_ten_million_needs_no_face_match(client, db, make_user, supervisor, officer):
    _, app_id = approved(client, db, make_user, supervisor, 10_000_000)
    assert disburse(client, officer[1], app_id).status_code == 201


def test_lf020_face_match_for_small_amount_is_refused(client, db, make_user, supervisor, officer):
    _, app_id = approved(client, db, make_user, supervisor, 5_000_000)
    assert face_match(client, officer[1], app_id).status_code == 409


def test_lf020_face_match_token_is_single_use(client, db, make_user, supervisor, officer):
    _, app_id = approved(client, db, make_user, supervisor, 12_000_000)
    match = face_match(client, officer[1], app_id).json()
    assert disburse(client, officer[1], app_id, match["id"]).status_code == 201

    again = disburse(client, officer[1], app_id, match["id"])

    assert again.status_code == 409  # already disbursed; one payout per loan


def test_lf020_used_token_cannot_back_another_attempt(client, db, make_user, supervisor, officer):
    from app.models.disbursement import FaceMatch

    _, app_id = approved(client, db, make_user, supervisor, 12_000_000)
    match = face_match(client, officer[1], app_id).json()
    db.get(FaceMatch, uuid.UUID(match["id"])).consumed_at = db.get(
        FaceMatch, uuid.UUID(match["id"])
    ).created_at
    db.commit()

    response = disburse(client, officer[1], app_id, match["id"])

    assert response.status_code == 403
    assert "already used" in response.json()["detail"]


def test_lf020_expired_face_match_is_refused(client, db, clock, make_user, supervisor, officer):
    _, app_id = approved(client, db, make_user, supervisor, 12_000_000)
    match = face_match(client, officer[1], app_id).json()
    clock.advance(minutes=6)

    response = disburse(client, officer[1], app_id, match["id"])

    assert response.status_code == 403
    assert "expired" in response.json()["detail"]


def test_lf020_face_match_from_another_application_is_refused(
    client, db, make_user, supervisor, officer
):
    _, first = approved(client, db, make_user, supervisor, 12_000_000)
    _, second = approved(client, db, make_user, supervisor, 12_000_000)
    match = face_match(client, officer[1], first).json()

    response = disburse(client, officer[1], second, match["id"])

    assert response.status_code == 403


def test_lf020_only_approved_applications_are_disbursed(client, db, make_user, officer):
    _, headers, app_id = new_application(client, make_user)
    upload_all(client, headers, app_id)  # IN_REVIEW, not approved

    assert disburse(client, officer[1], app_id).status_code == 409


def test_lf020_borrower_cannot_disburse_or_match(client, db, make_user, supervisor):
    headers, app_id = approved(client, db, make_user, supervisor, 12_000_000)

    assert disburse(client, headers, app_id).status_code == 403
    assert face_match(client, headers, app_id).status_code == 403
    assert client.get(f"/applications/{app_id}/disbursement", headers=headers).status_code == 403


def test_lf020_disbursement_is_append_only(client, db, make_user, supervisor, officer):
    _, app_id = approved(client, db, make_user, supervisor, 5_000_000)
    disburse(client, officer[1], app_id)
    row = db.scalar(select(Disbursement))

    row.amount_vnd = Decimal(1)
    with pytest.raises(DisbursementImmutable):
        db.flush()
    db.rollback()
    with pytest.raises(DBAPIError):
        db.execute(text("UPDATE disbursements SET amount_vnd = 1"))
    db.rollback()
