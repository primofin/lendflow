"""D-005: the API's database role can append to audit_logs and decisions but not change them."""

import psycopg
import pytest
from psycopg import errors
from sqlalchemy import Engine

from scripts.provision_app_role import provision

ROLE = "lendflow_app_test"
PASSWORD = "a-long-test-password-1"


@pytest.fixture
def owner_and_app(engine: Engine):
    url = engine.url.set(drivername="postgresql").render_as_string(hide_password=False)
    owner = psycopg.connect(url, autocommit=True)
    provision(owner, ROLE, PASSWORD)
    app_url = engine.url.set(
        drivername="postgresql", username=ROLE, password=PASSWORD
    ).render_as_string(hide_password=False)
    app = psycopg.connect(app_url)  # never committed: audit rows cannot be deleted afterwards
    yield owner, app
    app.rollback()
    app.close()
    owner.execute(f"DROP OWNED BY {ROLE}")
    owner.execute(f"DROP ROLE {ROLE}")
    owner.close()


def test_app_role_can_insert_and_read_audit_log(owner_and_app):
    _, app = owner_and_app
    app.execute(
        "INSERT INTO audit_logs (id, action, created_at) VALUES (gen_random_uuid(), 'x', now())"
    )
    assert app.execute("SELECT count(*) FROM audit_logs").fetchone()[0] >= 1


@pytest.mark.parametrize(
    "statement",
    [
        "DELETE FROM audit_logs",
        "UPDATE audit_logs SET action = 'y'",
        "TRUNCATE audit_logs",
        "DELETE FROM decisions",
        "UPDATE decisions SET decided_by = decided_by",
        "DROP TRIGGER audit_logs_no_update_delete ON audit_logs",
    ],
)
def test_app_role_cannot_change_append_only_tables(owner_and_app, statement):
    _, app = owner_and_app
    with pytest.raises(errors.InsufficientPrivilege):
        app.execute(statement)


def test_app_role_can_write_ordinary_tables(owner_and_app):
    _, app = owner_and_app
    app.execute("SELECT 1 FROM users LIMIT 1")
    app.execute("DELETE FROM outbox")


def test_provision_rejects_weak_input(owner_and_app):
    owner, _ = owner_and_app
    with pytest.raises(ValueError):
        provision(owner, "Bad-Role;", PASSWORD)
    with pytest.raises(ValueError):
        provision(owner, ROLE, "short")
