"""LF-001 Register and log in. Acceptance criteria: docs/04-user-stories-backlog.md."""

import pytest
from sqlalchemy import func, select

from app.models.audit_log import AuditLog
from app.models.user import Role, User

PASSWORD = "correct-horse-battery"  # >= 10 chars, synthetic


def register(client, email="an.nguyen@example.com", password=PASSWORD):
    return client.post("/auth/register", json={"email": email, "password": password})


def login(client, email="an.nguyen@example.com", password=PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


# --- Registration ---------------------------------------------------------


def test_lf001_register_creates_account_and_returns_tokens(client):
    response = register(client)

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    me = client.get("/auth/me", headers=bearer(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == "an.nguyen@example.com"


def test_lf001_register_rejects_password_shorter_than_10(client, db):
    response = register(client, password="short-pw1")  # 9 chars

    assert response.status_code == 422
    assert "at least 10 characters" in response.text
    assert db.scalar(select(func.count()).select_from(User)) == 0


@pytest.mark.parametrize("second_email", ["an.nguyen@example.com", "An.Nguyen@Example.COM"])
def test_lf001_register_duplicate_email_returns_409_and_single_row(client, db, second_email):
    assert register(client).status_code == 201

    response = register(client, email=second_email)

    assert response.status_code == 409
    assert response.json()["detail"] == "This email is already registered"
    assert db.scalar(select(func.count()).select_from(User)) == 1


def test_lf001_register_always_assigns_borrower_role(client, db):
    response = client.post(
        "/auth/register",
        json={"email": "x@example.com", "password": PASSWORD, "role": "supervisor"},
    )

    assert response.status_code == 201
    user = db.scalar(select(User).where(User.email == "x@example.com"))
    assert user.role == Role.BORROWER


def test_lf001_password_is_stored_hashed(client, db):
    register(client)

    user = db.scalar(select(User))
    assert user.password_hash != PASSWORD
    assert user.password_hash.startswith("$argon2")


# --- Login ----------------------------------------------------------------


def test_lf001_login_success_returns_access_and_refresh(client):
    register(client)

    response = login(client)

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["refresh_token"]


@pytest.mark.parametrize(
    ("email", "password"),
    [("an.nguyen@example.com", "wrong-password-1"), ("nobody@example.com", PASSWORD)],
)
def test_lf001_login_wrong_credentials_returns_generic_401(client, email, password):
    register(client)

    response = login(client, email=email, password=password)

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


# --- Lockout --------------------------------------------------------------


def fail_login(client, times):
    for _ in range(times):
        login(client, password="wrong-password-1")


def test_lf001_five_failures_lock_account_15_minutes_and_audit(client, db):
    register(client)

    fail_login(client, 5)

    response = login(client)
    assert response.status_code == 423
    assert "15 minutes" in response.json()["detail"]
    user = db.scalar(select(User))
    actions = db.scalars(select(AuditLog.action).where(AuditLog.actor_id == user.id)).all()
    assert "auth.lockout" in actions


def test_lf001_four_failures_do_not_lock(client):
    register(client)

    fail_login(client, 4)

    assert login(client).status_code == 200


def test_lf001_locked_account_unlocks_after_15_minutes(client, clock):
    register(client)
    fail_login(client, 5)

    clock.advance(minutes=14, seconds=59)
    assert login(client).status_code == 423
    clock.advance(seconds=2)
    assert login(client).status_code == 200


def test_lf001_success_resets_failure_counter(client):
    register(client)
    fail_login(client, 4)
    assert login(client).status_code == 200

    fail_login(client, 4)

    assert login(client).status_code == 200


# --- Session: idle timeout, refresh, logout --------------------------------


def test_lf001_idle_30_minutes_logs_out(client, clock):
    tokens = register(client).json()

    clock.advance(minutes=31)

    assert client.get("/auth/me", headers=bearer(tokens["access_token"])).status_code == 401
    refresh = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 401


def test_lf001_activity_keeps_session_alive(client, clock):
    tokens = register(client).json()

    clock.advance(minutes=20)
    assert client.get("/auth/me", headers=bearer(tokens["access_token"])).status_code == 200
    clock.advance(minutes=20)  # 40 min since login, 20 since last activity

    assert client.get("/auth/me", headers=bearer(tokens["access_token"])).status_code == 200


def test_lf001_refresh_rotates_and_old_token_rejected(client):
    tokens = register(client).json()

    first = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == 200
    assert first.json()["refresh_token"] != tokens["refresh_token"]

    reused = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401


def test_lf001_logout_revokes_session(client):
    tokens = register(client).json()
    headers = bearer(tokens["access_token"])

    assert client.post("/auth/logout", headers=headers).status_code == 204

    assert client.get("/auth/me", headers=headers).status_code == 401
    refresh = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 401


@pytest.mark.parametrize("token", ["not-a-jwt", None])
def test_lf001_invalid_or_missing_token_rejected(client, token):
    headers = bearer(token) if token else {}

    assert client.get("/auth/me", headers=headers).status_code == 401


def test_lf001_tampered_jwt_rejected(client):
    access = register(client).json()["access_token"]
    header, payload, signature = access.split(".")
    tampered = f"{header}.{payload}.{signature[:-4]}AAAA"

    assert client.get("/auth/me", headers=bearer(tampered)).status_code == 401
