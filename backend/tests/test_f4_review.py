"""F4: the staff file view (GET /applications/{id}/review)."""

import uuid

from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.user import Role

from .test_lf010_queue import new_application, queued


def review(client, headers, app_id):
    return client.get(f"/applications/{app_id}/review", headers=headers)


def test_f4_officer_sees_loan_and_applicant_with_masked_national_id(client, make_user):
    _, _, app_id = new_application(client, make_user, name="Tran Thi Binh")
    _, officer = make_user(Role.OFFICER)

    response = review(client, officer, app_id)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == app_id
    assert body["applicant"]["full_name"] == "Tran Thi Binh"
    assert body["applicant"]["national_id_masked"].endswith("8901")
    assert set(body["applicant"]["national_id_masked"][:-4]) == {"*"}
    assert len(body["applicant"]["national_id_masked"]) == 12
    assert "national_id" not in body["applicant"]
    assert body["flags"] == []
    assert body["assigned"] is False and body["assigned_to_me"] is False


def test_f4_claim_is_reflected_for_the_claimer_and_hidden_identity_for_others(
    client, db, make_user
):
    app_id = queued(client, make_user, db)
    _, officer = make_user(Role.OFFICER)
    _, supervisor = make_user(Role.SUPERVISOR)
    client.post(f"/applications/{app_id}/claim", headers=officer)

    mine = review(client, officer, app_id).json()
    seen_by_supervisor = review(client, supervisor, app_id).json()

    assert mine["assigned"] and mine["assigned_to_me"]
    assert seen_by_supervisor["assigned"] and not seen_by_supervisor["assigned_to_me"]


def test_f4_another_officers_file_is_refused_and_audited(client, db, make_user):
    app_id = queued(client, make_user, db)
    _, first = make_user(Role.OFFICER)
    second_user, second = make_user(Role.OFFICER)
    client.post(f"/applications/{app_id}/claim", headers=first)

    response = review(client, second, app_id)

    assert response.status_code == 403
    denied = db.scalars(
        select(AuditLog).where(
            AuditLog.action == "application.access_denied", AuditLog.actor_id == second_user.id
        )
    ).all()
    assert len(denied) == 1


def test_f4_borrowers_and_anonymous_cannot_use_the_file_view(client, make_user):
    _, headers, app_id = new_application(client, make_user)

    assert review(client, headers, app_id).status_code == 403
    assert client.get(f"/applications/{app_id}/review").status_code == 401


def test_f4_each_staff_read_is_audited_without_applicant_data(client, db, make_user):
    _, _, app_id = new_application(client, make_user, name="Le Van Cuong")
    officer_user, officer = make_user(Role.OFFICER)

    review(client, officer, app_id)

    rows = db.scalars(
        select(AuditLog).where(
            AuditLog.action == "application.read", AuditLog.actor_id == officer_user.id
        )
    ).all()
    assert len(rows) == 1
    assert "Le Van Cuong" not in str(rows[0].__dict__)


def test_f4_unknown_application_is_404(client, make_user):
    _, officer = make_user(Role.OFFICER)
    assert review(client, officer, str(uuid.uuid4())).status_code == 404
