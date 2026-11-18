"""LF-018 Data-subject rights (docs/04; BR-22, BR-14)."""

import json
import uuid
from datetime import timedelta

from sqlalchemy import select

from app.core.config import get_settings
from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.deletion_request import DeletionRequest
from app.models.user import Role

from .test_lf010_queue import new_application, upload_all

MY_DATA = "/me/data"
EXPORT = "/me/data/export"
DELETION = "/me/data/deletion-request"


def audit_actions(db, user_id):
    return list(
        db.scalars(
            select(AuditLog.action).where(AuditLog.actor_id == user_id).order_by(AuditLog.seq)
        )
    )


# --- AC1: view everything held and the purposes ----------------------------------------------


def test_lf018_my_data_lists_profile_applications_documents_consent_and_purposes(
    client, db, make_user
):
    owner, headers, app_id = new_application(client, make_user, name="Nguyen Van An")
    upload_all(client, headers, app_id)

    body = client.get(MY_DATA, headers=headers).json()

    assert body["account"]["email"] == owner.email
    assert body["profile"]["full_name"] == "Nguyen Van An"
    assert len(body["profile"]["national_id"]) == 12  # the borrower's own data, shown in full
    assert [a["id"] for a in body["applications"]] == [app_id]
    assert len(body["applications"][0]["documents"]) == 3
    assert body["consents"][0]["purposes"]
    assert {p["code"] for p in body["purposes"]} >= {"credit_scoring", "application_processing"}
    assert body["retention_months"] == get_settings().consent_retention_months
    assert body["deletion_request"] is None


def test_lf018_my_data_for_a_borrower_with_nothing_yet_is_empty_not_an_error(client, make_user):
    _, headers = make_user(Role.BORROWER)

    body = client.get(MY_DATA, headers=headers).json()

    assert body["profile"] is None
    assert body["applications"] == []
    assert body["consents"] == []


def test_lf018_my_data_never_includes_another_borrowers_data(client, make_user):
    _, mine, _ = new_application(client, make_user, name="Mine Person")
    _, _, _ = new_application(client, make_user, name="Someone Else")

    text = client.get(MY_DATA, headers=mine).text

    assert "Mine Person" in text
    assert "Someone Else" not in text


def test_lf018_my_data_includes_decisions_on_my_applications(client, db, make_user):
    _, headers, app_id = new_application(client, make_user)
    upload_all(client, headers, app_id)
    officer = make_user(Role.OFFICER)
    assert client.post(f"/applications/{app_id}/claim", headers=officer[1]).status_code == 200
    decided = client.post(
        f"/applications/{app_id}/decision", headers=officer[1], json={"outcome": "approve"}
    )
    assert decided.status_code == 201

    body = client.get(MY_DATA, headers=headers).json()

    assert body["applications"][0]["status"] == "APPROVED"
    assert [d["outcome"] for d in body["applications"][0]["decisions"]] == ["approve"]


# --- AC2: machine-readable export ------------------------------------------------------------


def test_lf018_export_is_a_json_download_of_only_my_data_without_secrets(client, db, make_user):
    owner, headers, _ = new_application(client, make_user, name="Export Person")
    new_application(client, make_user, name="Other Person")

    response = client.get(EXPORT, headers=headers)

    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    body = json.loads(response.text)
    assert body["account"]["email"] == owner.email
    assert body["profile"]["full_name"] == "Export Person"
    assert "exported_at" in body
    assert "Other Person" not in response.text
    for secret in ("password", "hash", "token", "$argon2", "$2b$"):
        assert secret not in response.text.lower()
    assert "data.exported" in audit_actions(db, owner.id)


# --- AC3: deletion request with a due date, visible to a supervisor --------------------------


def test_lf018_deletion_request_gets_a_due_date_and_a_supervisor_can_see_it(
    client, db, clock, make_user
):
    owner, headers, _ = new_application(client, make_user)
    supervisor = make_user(Role.SUPERVISOR)

    created = client.post(DELETION, headers=headers)

    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "open"
    assert body["due_at"].startswith(
        (clock() + timedelta(days=get_settings().deletion_request_due_days)).strftime("%Y-%m-%d")
    )
    listed = client.get("/data-requests", headers=supervisor[1]).json()
    assert [(r["email"], r["status"], r["overdue"]) for r in listed] == [
        (owner.email, "open", False)
    ]
    assert "data.deletion_requested" in audit_actions(db, owner.id)
    shown = client.get(MY_DATA, headers=headers).json()["deletion_request"]
    assert shown["id"] == body["id"]


def test_lf018_due_days_come_from_settings(client, make_user, monkeypatch):
    monkeypatch.setattr(get_settings(), "deletion_request_due_days", 7)
    _, headers = make_user(Role.BORROWER)

    body = client.post(DELETION, headers=headers).json()

    from datetime import datetime

    gap = datetime.fromisoformat(body["due_at"]) - datetime.fromisoformat(body["requested_at"])
    assert gap == timedelta(days=7)


def test_lf018_request_becomes_overdue_after_its_due_date(client, clock, make_user):
    _, headers = make_user(Role.BORROWER)
    client.post(DELETION, headers=headers)

    clock.advance(days=get_settings().deletion_request_due_days + 1)
    supervisor = make_user(Role.SUPERVISOR)  # log in after the jump: tokens last 15 minutes

    assert client.get("/data-requests", headers=supervisor[1]).json()[0]["overdue"] is True


def test_lf018_second_request_while_one_is_open_is_refused(client, db, make_user):
    owner, headers, _ = new_application(client, make_user)
    client.post(DELETION, headers=headers)

    again = client.post(DELETION, headers=headers)

    assert again.status_code == 409
    assert "already have an open deletion request" in again.json()["detail"]
    assert (
        len(db.scalars(select(DeletionRequest).where(DeletionRequest.user_id == owner.id)).all())
        == 1
    )


def test_lf018_requesting_deletion_deletes_nothing(client, db, make_user):
    _, headers, app_id = new_application(client, make_user)

    client.post(DELETION, headers=headers)

    body = client.get(MY_DATA, headers=headers).json()
    assert body["profile"] is not None
    assert [a["id"] for a in body["applications"]] == [app_id]


# --- AC4: active application, say what must be retained --------------------------------------


def test_lf018_active_application_is_listed_as_retained_with_a_reason(client, make_user):
    _, headers, _ = new_application(client, make_user)

    retained = client.post(DELETION, headers=headers).json()["retained"]

    whats = [r["what"] for r in retained]
    assert any(w.startswith("Application of") for w in whats)
    assert any("Audit log" in w for w in whats)
    assert all(r["reason"] for r in retained)


def test_lf018_a_finished_application_is_not_listed_as_retained(client, db, make_user):
    _, headers, app_id = new_application(client, make_user)
    db.get(Application, uuid.UUID(app_id)).status = "APPROVED"
    db.commit()

    retained = client.post(DELETION, headers=headers).json()["retained"]

    assert [r["what"] for r in retained] == ["Audit log entries and recorded decisions"]


# --- access control --------------------------------------------------------------------------


def test_lf018_staff_cannot_use_the_borrower_endpoints_and_the_refusal_is_audited(
    client, db, make_user
):
    officer = make_user(Role.OFFICER)

    assert client.get(MY_DATA, headers=officer[1]).status_code == 403
    assert client.get(EXPORT, headers=officer[1]).status_code == 403
    assert client.post(DELETION, headers=officer[1]).status_code == 403
    assert audit_actions(db, officer[0].id).count("access.denied") == 3


def test_lf018_only_a_supervisor_can_list_requests(client, make_user):
    borrower = make_user(Role.BORROWER)
    officer = make_user(Role.OFFICER)

    assert client.get("/data-requests", headers=borrower[1]).status_code == 403
    assert client.get("/data-requests", headers=officer[1]).status_code == 403


def test_lf018_every_endpoint_requires_login(client):
    assert client.get(MY_DATA).status_code == 401
    assert client.get(EXPORT).status_code == 401
    assert client.post(DELETION).status_code == 401
    assert client.get("/data-requests").status_code == 401
