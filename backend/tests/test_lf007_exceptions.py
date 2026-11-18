"""LF-007 exceptions: "No invoices available" flags the file and assigns a supervisor (BR-10)."""

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.core.errors import SupervisorApprovalRequired
from app.core.permissions import check_decision_authority
from app.models.application import Application
from app.models.application_exception import ApplicationException
from app.models.audit_log import AuditLog
from app.models.user import Role

from .test_lf004_submit import submit
from .test_lf005_upload import JPEG, upload

INVOICES = "Invoices or service contracts (last 3 months)"


def new_application(client, make_user, income_type="freelance"):
    owner, headers = make_user(Role.BORROWER)
    response = submit(client, headers, profile={"income_type": income_type})
    assert response.status_code == 201
    return owner, headers, response.json()["id"]


def requirement_id(client, headers, app_id, label):
    body = client.get(f"/applications/{app_id}/checklist", headers=headers).json()
    return next(r["id"] for r in body["requirements"] if r["label"] == label)


def declare(client, headers, app_id, req_id):
    return client.post(
        f"/applications/{app_id}/exceptions", headers=headers, json={"requirement_id": req_id}
    )


def application(db, app_id):
    db.expire_all()
    return db.get(Application, uuid.UUID(app_id))


def audit(db, action):
    return db.scalars(select(AuditLog).where(AuditLog.action == action)).all()


@pytest.fixture
def supervisor(make_user):
    return make_user(Role.SUPERVISOR)[0]


# --- AC3: officer ticks "No invoices available" ----------


def test_lf007_declaring_no_invoices_flags_the_file_and_assigns_a_supervisor(
    client, db, make_user, supervisor
):
    _, owner_headers, app_id = new_application(client, make_user)
    officer, headers = make_user(Role.OFFICER)

    response = declare(client, headers, app_id, requirement_id(client, headers, app_id, INVOICES))

    assert response.status_code == 201
    body = response.json()
    assert body["exception_flag"] is True and body["supervisor_assigned"] is True
    assert by_label(body)[INVOICES]["state"] == "waived"
    stored = application(db, app_id)
    assert stored.exception_flag is True and stored.assigned_supervisor == supervisor.id
    declared = audit(db, "application.exception_declared")
    assigned = audit(db, "application.supervisor_assigned")
    assert [d.actor_id for d in declared] == [officer.id]
    assert [str(d.application_id) for d in declared] == [app_id]
    assert [str(a.application_id) for a in assigned] == [app_id]
    assert owner_headers  # the borrower is unaffected


def by_label(body):
    return {r["label"]: r for r in body["requirements"]}


def test_lf007_an_officer_can_no_longer_approve_a_file_with_an_exception(
    client, db, make_user, supervisor
):
    _, _, app_id = new_application(client, make_user)
    _, headers = make_user(Role.OFFICER)
    declare(client, headers, app_id, requirement_id(client, headers, app_id, INVOICES))

    flagged = application(db, app_id)

    with pytest.raises(SupervisorApprovalRequired):
        check_decision_authority(
            Role.OFFICER, Decimal(10_000_000), exception_flag=flagged.exception_flag
        )
    check_decision_authority(
        Role.SUPERVISOR, Decimal(10_000_000), exception_flag=flagged.exception_flag
    )


def test_lf007_status_is_exception_only_when_everything_else_is_in_order(
    client, make_user, supervisor
):
    _, owner_headers, app_id = new_application(client, make_user)
    _, headers = make_user(Role.OFFICER)
    req = requirement_id(client, headers, app_id, INVOICES)

    still_missing = declare(client, headers, app_id, req).json()
    assert still_missing["status"] == "incomplete"  # national ID and bank statements missing
    upload(client, owner_headers, app_id, JPEG, doc_type="national_id")
    upload(client, owner_headers, app_id, JPEG, doc_type="bank_statements")

    body = client.get(f"/applications/{app_id}/checklist", headers=headers).json()

    assert body["status"] == "exception"


def test_lf007_declaring_the_same_requirement_twice_creates_no_duplicate(
    client, db, make_user, supervisor
):
    _, _, app_id = new_application(client, make_user)
    _, headers = make_user(Role.OFFICER)
    req = requirement_id(client, headers, app_id, INVOICES)

    first, again = declare(client, headers, app_id, req), declare(client, headers, app_id, req)

    assert first.status_code == 201 and again.status_code == 200
    assert db.scalar(select(func.count()).select_from(ApplicationException)) == 1
    assert len(audit(db, "application.exception_declared")) == 1


def test_lf007_a_second_exception_does_not_reassign_the_supervisor(client, db, make_user):
    first_sup, _ = make_user(Role.SUPERVISOR)
    _, _, app_id = new_application(client, make_user)
    _, headers = make_user(Role.OFFICER)
    declare(client, headers, app_id, requirement_id(client, headers, app_id, INVOICES))
    make_user(Role.SUPERVISOR)  # a newcomer must not take over the file

    declare(
        client,
        headers,
        app_id,
        requirement_id(client, headers, app_id, "Bank statements (last 6 months)"),
    )

    assert application(db, app_id).assigned_supervisor == first_sup.id
    assert len(audit(db, "application.supervisor_assigned")) == 1
    assert len(audit(db, "application.exception_declared")) == 2


# --- Rules for what can be declared ----------


def test_lf007_a_requirement_that_is_already_satisfied_cannot_be_declared_missing(
    client, db, make_user, supervisor
):
    _, owner_headers, app_id = new_application(client, make_user)
    upload(client, owner_headers, app_id, JPEG, doc_type="invoices_contracts")
    _, headers = make_user(Role.OFFICER)

    response = declare(client, headers, app_id, requirement_id(client, headers, app_id, INVOICES))

    assert response.status_code == 409 and "already" in response.json()["detail"]
    assert application(db, app_id).exception_flag is False


def test_lf007_an_optional_requirement_cannot_be_declared(client, make_user, supervisor):
    _, _, app_id = new_application(client, make_user)
    _, headers = make_user(Role.OFFICER)

    response = declare(
        client, headers, app_id, requirement_id(client, headers, app_id, "Business licence")
    )

    assert response.status_code == 409 and "optional" in response.json()["detail"]


def test_lf007_requirement_from_another_income_type_or_unknown_is_404(
    client, make_user, supervisor
):
    _, _, freelance_app = new_application(client, make_user)
    _, other_headers, rental_app = new_application(client, make_user, income_type="rental")
    _, headers = make_user(Role.OFFICER)
    rental_req = requirement_id(client, headers, rental_app, "Rental contract")

    assert declare(client, headers, freelance_app, rental_req).status_code == 404
    assert declare(client, headers, freelance_app, str(uuid.uuid4())).status_code == 404
    assert declare(client, headers, str(uuid.uuid4()), rental_req).status_code == 404
    assert other_headers


def test_lf007_the_request_cannot_carry_free_text(client, db, make_user, supervisor):
    _, _, app_id = new_application(client, make_user)
    _, headers = make_user(Role.OFFICER)
    req = requirement_id(client, headers, app_id, INVOICES)

    response = client.post(
        f"/applications/{app_id}/exceptions",
        headers=headers,
        json={"requirement_id": req, "note": "borrower is Nguyen Van An, CCCD 012345678901"},
    )

    assert response.status_code == 201
    assert "Nguyen" not in response.text
    stored = db.scalar(select(ApplicationException))
    assert not hasattr(stored, "note")


# --- Access ----------


@pytest.mark.parametrize("role", [Role.BORROWER, Role.SUPERVISOR])
def test_lf007_only_officers_can_declare_exceptions(client, db, make_user, supervisor, role):
    _, owner_headers, app_id = new_application(client, make_user)
    _, officer_headers = make_user(Role.OFFICER)
    req = requirement_id(client, officer_headers, app_id, INVOICES)
    actor, headers = (None, owner_headers) if role == Role.BORROWER else make_user(Role.SUPERVISOR)

    response = declare(client, headers, app_id, req)

    assert response.status_code == 403
    assert application(db, app_id).exception_flag is False
    assert db.scalar(select(func.count()).select_from(ApplicationException)) == 0
    assert actor is None or actor


def test_lf007_declaring_requires_login(client, make_user):
    _, _, app_id = new_application(client, make_user)

    response = client.post(
        f"/applications/{app_id}/exceptions", json={"requirement_id": str(uuid.uuid4())}
    )

    assert response.status_code == 401


# --- Automatic assignment ----------


def test_lf007_no_active_supervisor_still_records_the_exception_unassigned(client, db, make_user):
    make_user(Role.SUPERVISOR, active=False)
    _, _, app_id = new_application(client, make_user)
    _, headers = make_user(Role.OFFICER)

    response = declare(client, headers, app_id, requirement_id(client, headers, app_id, INVOICES))

    assert response.status_code == 201
    assert response.json()["exception_flag"] is True
    assert response.json()["supervisor_assigned"] is False
    stored = application(db, app_id)
    assert stored.exception_flag is True and stored.assigned_supervisor is None
    assert audit(db, "application.supervisor_assigned") == []


def test_lf007_assignment_goes_to_the_least_loaded_supervisor_oldest_first_on_ties(
    client, db, make_user
):
    older, _ = make_user(Role.SUPERVISOR)
    newer, _ = make_user(Role.SUPERVISOR)
    newer.created_at = older.created_at + timedelta(hours=1)
    db.commit()
    _, officer_headers = make_user(Role.OFFICER)

    assigned = []
    for _ in range(4):
        _, _, app_id = new_application(client, make_user)
        declare(
            client,
            officer_headers,
            app_id,
            requirement_id(client, officer_headers, app_id, INVOICES),
        )
        assigned.append(application(db, app_id).assigned_supervisor)

    # tie -> older; then newer has fewer; tie -> older; then newer again
    assert assigned == [older.id, newer.id, older.id, newer.id]


def test_lf007_inactive_supervisors_are_never_assigned(client, db, make_user):
    make_user(Role.SUPERVISOR, active=False)
    active, _ = make_user(Role.SUPERVISOR)
    _, _, app_id = new_application(client, make_user)
    _, headers = make_user(Role.OFFICER)

    declare(client, headers, app_id, requirement_id(client, headers, app_id, INVOICES))

    assert application(db, app_id).assigned_supervisor == active.id


# --- "Other" income type escalates automatically (docs/02) ----------


def test_lf007_other_income_type_is_flagged_and_assigned_at_submission(
    client, db, make_user, supervisor
):
    _, _, app_id = new_application(client, make_user, income_type="other")

    stored = application(db, app_id)

    assert stored.exception_flag is True and stored.assigned_supervisor == supervisor.id
    assigned = audit(db, "application.supervisor_assigned")
    assert [str(a.application_id) for a in assigned] == [app_id]


@pytest.mark.parametrize("income_type", ["salaried", "freelance", "self_employed", "rental"])
def test_lf007_other_income_types_are_not_escalated_at_submission(
    client, db, make_user, supervisor, income_type
):
    _, _, app_id = new_application(client, make_user, income_type=income_type)

    stored = application(db, app_id)

    assert stored.exception_flag is False and stored.assigned_supervisor is None
    assert audit(db, "application.supervisor_assigned") == []


def test_lf007_other_income_type_without_any_supervisor_still_submits(client, db, make_user):
    _, _, app_id = new_application(client, make_user, income_type="other")

    stored = application(db, app_id)

    assert stored.exception_flag is True and stored.assigned_supervisor is None
