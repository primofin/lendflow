"""LF-016 AC2: audit entries cannot be edited or deleted through the application (BR-14)."""

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.models.audit_log import AuditLog, AuditLogImmutable
from app.models.user import Role
from app.services import audit_service


@pytest.fixture
def entry(db, clock):
    audit_service.record(db, action="test.original", now=clock(), ip_address="10.0.0.1")
    db.commit()
    return db.scalar(select(AuditLog).where(AuditLog.action == "test.original"))


def attempt(db, sql: str, **params):
    """Run a statement inside a savepoint so a refusal does not poison the test transaction."""
    with pytest.raises(DBAPIError, match="append-only"), db.begin_nested():
        db.execute(text(sql), params)


# --- Database triggers: hold for every connection, including a superuser ----------


def test_lf016_database_rejects_update(db, entry):
    attempt(db, "UPDATE audit_logs SET action = 'tampered'")

    db.refresh(entry)
    assert entry.action == "test.original"


def test_lf016_database_rejects_delete(db, entry):
    attempt(db, "DELETE FROM audit_logs")

    assert db.scalar(select(AuditLog).where(AuditLog.id == entry.id)) is not None


def test_lf016_database_rejects_truncate(db, entry):
    attempt(db, "TRUNCATE audit_logs")

    assert db.scalar(select(AuditLog).where(AuditLog.id == entry.id)) is not None


def test_lf016_database_rejects_single_row_update_by_id(db, entry):
    attempt(db, "UPDATE audit_logs SET ip_address = '1.2.3.4' WHERE id = :id", id=entry.id)

    db.refresh(entry)
    assert entry.ip_address == "10.0.0.1"


def test_lf016_tests_run_as_superuser_so_triggers_are_what_protect_the_table(db):
    # Documents why a REVOKE would not be enough in this setup (see D-012).
    assert db.scalar(text("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")) is True


def test_lf016_appending_still_works_and_gets_increasing_seq(db, clock):
    for name in ("a", "b", "c"):
        audit_service.record(db, action=f"test.{name}", now=clock())
    db.commit()

    seqs = db.scalars(select(AuditLog.seq).order_by(AuditLog.seq)).all()

    assert len(seqs) == 3 and seqs == sorted(set(seqs))


# --- ORM guard: fail fast with a clear error before the database is even reached ---------------


def test_lf016_orm_refuses_to_modify_an_entry(db, entry):
    entry.action = "tampered"

    with pytest.raises(AuditLogImmutable):
        db.flush()
    db.rollback()


def test_lf016_orm_refuses_to_delete_an_entry(db, entry):
    db.delete(entry)

    with pytest.raises(AuditLogImmutable):
        db.flush()
    db.rollback()


# --- No write routes ----------


def test_lf016_audit_log_has_only_read_routes(client):
    # The OpenAPI schema lists every real operation, including those of included routers.
    paths = {p: ops for p, ops in client.app.openapi()["paths"].items() if "/audit-logs" in p}

    assert paths, "the audit log endpoint must exist"
    for path, operations in paths.items():
        assert set(operations) <= {"get"}, (path, set(operations))


@pytest.mark.parametrize("method", ["put", "patch", "delete", "post"])
def test_lf016_write_methods_are_not_allowed_even_for_a_supervisor(client, make_user, method):
    _, headers = make_user(Role.SUPERVISOR)

    response = client.request(method, "/audit-logs", headers=headers)

    assert response.status_code in (404, 405)
