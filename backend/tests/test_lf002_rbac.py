"""LF-002 Role-based access control. Matrix: docs/01-stakeholders-and-rbac.md."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.borrower_profile import BorrowerProfile
from app.models.user import Role, User


def make_application(db, owner, *, created_by=None, amount_vnd=100_000_000):
    profile = db.scalar(select(BorrowerProfile).where(BorrowerProfile.user_id == owner.id))
    if profile is None:
        profile = BorrowerProfile(user_id=owner.id)
        db.add(profile)
        db.flush()
    application = Application(
        borrower_profile_id=profile.id,
        created_by=(created_by or owner).id,
        amount_vnd=Decimal(amount_vnd),
        term_months=24,
    )
    db.add(application)
    db.commit()
    return application


def audit_actions(db, actor_id):
    return db.scalars(select(AuditLog.action).where(AuditLog.actor_id == actor_id)).all()


# --- Application ownership (AC1) -------------------------------------------


def test_lf002_borrower_reads_own_application_200(client, db, make_user):
    borrower, headers = make_user(Role.BORROWER)
    application = make_application(db, borrower)

    response = client.get(f"/applications/{application.id}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == str(application.id)
    assert response.json()["amount_vnd"] == 100_000_000


def test_lf002_borrower_reads_other_application_403_and_audited(client, db, make_user):
    owner, _ = make_user(Role.BORROWER)
    intruder, headers = make_user(Role.BORROWER)
    application = make_application(db, owner)

    response = client.get(f"/applications/{application.id}", headers=headers)

    assert response.status_code == 403
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "application.access_denied"))
    assert entry.actor_id == intruder.id
    assert entry.target_id == application.id


def test_lf002_missing_application_404(client, make_user):
    _, headers = make_user(Role.BORROWER)

    response = client.get(f"/applications/{uuid.uuid4()}", headers=headers)

    assert response.status_code == 404


@pytest.mark.parametrize("role", [Role.OFFICER, Role.SUPERVISOR])
def test_lf002_staff_can_read_application_and_read_is_audited(client, db, make_user, role):
    borrower, _ = make_user(Role.BORROWER)
    staff, headers = make_user(role)
    application = make_application(db, borrower)

    response = client.get(f"/applications/{application.id}", headers=headers)

    assert response.status_code == 200
    assert "application.read" in audit_actions(db, staff.id)


def test_lf002_unauthenticated_request_401(client, db, make_user):
    borrower, _ = make_user(Role.BORROWER)
    application = make_application(db, borrower)

    assert client.get(f"/applications/{application.id}").status_code == 401


def test_lf002_inactive_user_token_rejected(client, db, make_user):
    borrower, headers = make_user(Role.BORROWER, active=False)
    application = make_application(db, borrower)

    assert client.get(f"/applications/{application.id}", headers=headers).status_code == 401


# --- User management (AC3) --------------------------------------------------


def test_lf002_supervisor_lists_users(client, make_user):
    _, headers = make_user(Role.SUPERVISOR)
    make_user(Role.OFFICER)

    response = client.get("/users", headers=headers)

    assert response.status_code == 200
    assert {u["role"] for u in response.json()} >= {"supervisor", "officer"}


def test_lf002_supervisor_creates_user_with_role_and_audits(client, db, make_user):
    supervisor, headers = make_user(Role.SUPERVISOR)

    response = client.post(
        "/users",
        headers=headers,
        json={"email": "new.officer@example.com", "password": "officer-pass-1", "role": "officer"},
    )

    assert response.status_code == 201
    assert response.json()["role"] == "officer"
    created = db.scalar(select(User).where(User.email == "new.officer@example.com"))
    assert created.role == Role.OFFICER
    assert "user.create" in audit_actions(db, supervisor.id)


def test_lf002_supervisor_create_duplicate_email_409(client, make_user):
    existing, _ = make_user(Role.BORROWER)
    _, headers = make_user(Role.SUPERVISOR)

    response = client.post(
        "/users",
        headers=headers,
        json={"email": existing.email.upper(), "password": "officer-pass-1", "role": "officer"},
    )

    assert response.status_code == 409


def test_lf002_supervisor_changes_role_and_audits(client, db, make_user):
    supervisor, headers = make_user(Role.SUPERVISOR)
    target, _ = make_user(Role.BORROWER)

    response = client.patch(f"/users/{target.id}/role", headers=headers, json={"role": "officer"})

    assert response.status_code == 200
    db.refresh(target)
    assert target.role == Role.OFFICER
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "user.role_change"))
    assert entry.actor_id == supervisor.id
    assert entry.target_id == target.id


def test_lf002_supervisor_cannot_change_own_role(client, db, make_user):
    supervisor, headers = make_user(Role.SUPERVISOR)

    response = client.patch(
        f"/users/{supervisor.id}/role", headers=headers, json={"role": "borrower"}
    )

    assert response.status_code == 409
    db.refresh(supervisor)
    assert supervisor.role == Role.SUPERVISOR


def test_lf002_change_role_of_missing_user_404(client, make_user):
    _, headers = make_user(Role.SUPERVISOR)

    response = client.patch(
        f"/users/{uuid.uuid4()}/role", headers=headers, json={"role": "officer"}
    )

    assert response.status_code == 404


USER_ENDPOINTS = [
    ("get", "/users", None),
    ("post", "/users", {"email": "x@example.com", "password": "some-pass-12", "role": "officer"}),
    ("patch", "/users/00000000-0000-4000-8000-000000000000/role", {"role": "supervisor"}),
]


@pytest.mark.parametrize("role", [Role.BORROWER, Role.OFFICER])
@pytest.mark.parametrize(("method", "path", "body"), USER_ENDPOINTS)
def test_lf002_non_supervisor_gets_403_on_user_management(
    client, db, make_user, role, method, path, body
):
    user, headers = make_user(role)

    response = client.request(method, path, headers=headers, json=body)

    assert response.status_code == 403
    assert "access.denied" in audit_actions(db, user.id)
    assert db.scalar(select(User).where(User.email == "x@example.com")) is None
