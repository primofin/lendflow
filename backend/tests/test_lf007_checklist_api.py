"""LF-007 API: panel by income type, checklist per application. Acceptance: docs/04, BR-06."""

import uuid

import pytest
from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.user import Role

from .test_lf004_submit import submit
from .test_lf005_upload import JPEG, upload

SALARIED_MANDATORY = [
    "National ID",
    "Labour contract or employer confirmation",
    "Payslips or bank statements (last 3 months)",
]


def new_application(client, make_user, income_type="salaried"):
    owner, headers = make_user(Role.BORROWER)
    response = submit(client, headers, profile={"income_type": income_type})
    assert response.status_code == 201
    return owner, headers, response.json()["id"]


def panel(client, headers, income_type):
    return client.get(f"/income-types/{income_type}/requirements", headers=headers)


def checklist(client, headers, app_id):
    return client.get(f"/applications/{app_id}/checklist", headers=headers)


def by_label(body):
    return {r["label"]: r for r in body["requirements"]}


# --- Panel (AC1, AC2) ----------


def test_lf007_freelance_panel_lists_mandatory_and_optional(client, make_user):
    _, headers = make_user(Role.OFFICER)

    body = panel(client, headers, "freelance").json()

    assert body["income_type"] == "freelance"
    assert [r["label"] for r in body["mandatory"]] == [
        "National ID",
        "Invoices or service contracts (last 3 months)",
        "Bank statements (last 6 months)",
    ]
    assert [r["label"] for r in body["optional"]] == [
        "Business licence",
        "Personal income tax return",
    ]
    assert body["mandatory"][1]["doc_types"] == ["invoices_contracts"]


def test_lf007_self_employed_panel_requires_business_licence(client, make_user):
    _, headers = make_user(Role.OFFICER)

    body = panel(client, headers, "self_employed").json()

    assert "Business licence" in [r["label"] for r in body["mandatory"]]


def test_lf007_salaried_panel_shows_only_the_standard_list(client, make_user):
    _, headers = make_user(Role.OFFICER)

    body = panel(client, headers, "salaried").json()

    assert [r["label"] for r in body["mandatory"]] == SALARIED_MANDATORY
    assert [r["label"] for r in body["optional"]] == ["Tax return"]
    everything = " ".join(r["label"] for r in body["mandatory"] + body["optional"])
    assert "invoice" not in everything.lower() and "licence" not in everything.lower()


def test_lf007_or_requirements_list_all_alternatives(client, make_user):
    _, headers = make_user(Role.SUPERVISOR)

    body = panel(client, headers, "salaried").json()

    contract = next(r for r in body["mandatory"] if r["label"].startswith("Labour contract"))
    assert set(contract["doc_types"]) == {"labour_contract", "employer_confirmation"}


@pytest.mark.parametrize("income_type", ["lottery", "SALARIED", "salaried ", "0"])
def test_lf007_unknown_income_type_404(client, make_user, income_type):
    _, headers = make_user(Role.OFFICER)

    assert panel(client, headers, income_type).status_code == 404


def test_lf007_borrower_cannot_read_the_rules_panel(client, db, make_user):
    borrower, headers = make_user(Role.BORROWER)

    assert panel(client, headers, "salaried").status_code == 403
    denied = db.scalars(select(AuditLog.action).where(AuditLog.actor_id == borrower.id)).all()
    assert "access.denied" in denied


def test_lf007_panel_requires_login(client):
    assert client.get("/income-types/salaried/requirements").status_code == 401


# --- Checklist (AC4) ----------


def test_lf007_new_application_starts_incomplete_with_everything_missing(client, make_user):
    _, headers, app_id = new_application(client, make_user)

    body = checklist(client, headers, app_id).json()

    assert body["status"] == "incomplete" and body["income_type"] == "salaried"
    assert body["application_id"] == app_id
    mandatory = [r for r in body["requirements"] if r["mandatory"]]
    assert [r["label"] for r in mandatory] == SALARIED_MANDATORY
    assert {r["state"] for r in body["requirements"]} == {"missing"}
    assert body["exception_flag"] is False and body["supervisor_assigned"] is False


def test_lf007_all_mandatory_documents_present_shows_complete(client, make_user):
    _, headers, app_id = new_application(client, make_user)
    for doc_type in ("national_id", "labour_contract", "payslips"):
        assert upload(client, headers, app_id, JPEG, doc_type=doc_type).status_code == 201

    body = checklist(client, headers, app_id).json()

    assert body["status"] == "complete"
    assert {r["state"] for r in body["requirements"] if r["mandatory"]} == {"satisfied"}
    assert by_label(body)["Tax return"]["state"] == "missing"  # optional, does not block


@pytest.mark.parametrize(
    ("alternative", "label"),
    [
        ("employer_confirmation", "Labour contract or employer confirmation"),
        ("bank_statements", "Payslips or bank statements (last 3 months)"),
    ],
)
def test_lf007_either_alternative_satisfies_the_requirement(client, make_user, alternative, label):
    _, headers, app_id = new_application(client, make_user)
    uploaded = upload(client, headers, app_id, JPEG, doc_type=alternative).json()

    requirement = by_label(checklist(client, headers, app_id).json())[label]

    assert requirement["state"] == "satisfied"
    assert requirement["document_ids"] == [uploaded["id"]]


def test_lf007_missing_one_mandatory_document_keeps_it_incomplete(client, make_user):
    _, headers, app_id = new_application(client, make_user)
    upload(client, headers, app_id, JPEG, doc_type="national_id")
    upload(client, headers, app_id, JPEG, doc_type="payslips")

    body = checklist(client, headers, app_id).json()

    assert body["status"] == "incomplete"
    assert by_label(body)["Labour contract or employer confirmation"]["state"] == "missing"


def test_lf007_document_of_a_type_the_income_type_does_not_use_changes_nothing(client, make_user):
    _, headers, app_id = new_application(client, make_user)
    upload(client, headers, app_id, JPEG, doc_type="business_licence")

    body = checklist(client, headers, app_id).json()

    assert body["status"] == "incomplete"
    assert "Business licence" not in by_label(body)


def test_lf007_checklist_follows_the_applications_income_type(client, make_user):
    _, headers, app_id = new_application(client, make_user, income_type="rental")

    body = checklist(client, headers, app_id).json()

    assert [r["label"] for r in body["requirements"] if r["mandatory"]] == [
        "National ID",
        "Rental contract",
        "Proof of ownership",
    ]


# --- Access ----------


def test_lf007_borrower_cannot_read_another_borrowers_checklist(client, db, make_user):
    _, _, app_id = new_application(client, make_user)
    intruder, headers = make_user(Role.BORROWER)

    response = checklist(client, headers, app_id)

    assert response.status_code == 403
    denied = db.scalar(
        select(AuditLog).where(
            AuditLog.action == "application.access_denied", AuditLog.actor_id == intruder.id
        )
    )
    assert denied is not None and str(denied.application_id) == app_id


@pytest.mark.parametrize("role", [Role.OFFICER, Role.SUPERVISOR])
def test_lf007_staff_can_read_any_checklist_and_the_read_is_audited(client, db, make_user, role):
    _, _, app_id = new_application(client, make_user)
    staff, headers = make_user(role)

    assert checklist(client, headers, app_id).status_code == 200
    actions = db.scalars(select(AuditLog.action).where(AuditLog.actor_id == staff.id)).all()
    assert "application.read" in actions


def test_lf007_checklist_requires_login_and_a_real_application(client, make_user):
    _, headers, app_id = new_application(client, make_user)

    assert client.get(f"/applications/{app_id}/checklist").status_code == 401
    assert checklist(client, headers, str(uuid.uuid4())).status_code == 404


def test_lf007_checklist_does_not_expose_personal_data_or_the_assigned_supervisors_identity(
    client, make_user
):
    _, headers, app_id = new_application(client, make_user)

    text = checklist(client, headers, app_id).text

    assert "012345678901" not in text and "Nguyen Van An" not in text
    assert "assigned_supervisor_id" not in text


def test_lf007_a_later_application_with_another_income_type_does_not_change_an_earlier_checklist(
    client, make_user
):
    owner, headers = make_user(Role.BORROWER)
    first = submit(client, headers, profile={"income_type": "salaried"}).json()["id"]
    submit(client, headers, profile={"income_type": "freelance"})  # rewrites the profile

    body = checklist(client, headers, first).json()

    assert body["income_type"] == "salaried"
    assert [r["label"] for r in body["requirements"] if r["mandatory"]] == SALARIED_MANDATORY
    assert owner
