"""LF-016 migration 0006 on a scratch database: backfill happens BEFORE the triggers lock rows."""

import uuid
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from app.core.config import get_settings

SCRATCH_DB = "lendflow_migration_scratch"


@pytest.fixture
def scratch_url() -> Iterator[str]:
    base = make_url(get_settings().test_database_url)
    admin = create_engine(base.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {SCRATCH_DB} WITH (FORCE)"))
        conn.execute(text(f"CREATE DATABASE {SCRATCH_DB}"))
    yield base.set(database=SCRATCH_DB).render_as_string(hide_password=False)
    with admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {SCRATCH_DB} WITH (FORCE)"))
    admin.dispose()


def alembic_config(url: str) -> Config:
    cfg = Config("alembic.ini")
    cfg.attributes["database_url"] = url
    return cfg


def test_lf016_migration_backfills_application_id_then_locks_the_table(scratch_url):
    cfg = alembic_config(scratch_url)
    command.upgrade(cfg, "0005")
    engine = create_engine(scratch_url)
    ids = {name: str(uuid.uuid4()) for name in ("user", "profile", "app", "other_app", "doc")}
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, role, is_active, failed_login_count)"
                " VALUES (:u, 'old@example.com', 'x', 'borrower', true, 0)"
            ),
            {"u": ids["user"]},
        )
        conn.execute(
            text("INSERT INTO borrower_profiles (id, user_id) VALUES (:p, :u)"),
            {"p": ids["profile"], "u": ids["user"]},
        )
        for app_id in (ids["app"], ids["other_app"]):
            conn.execute(
                text(
                    "INSERT INTO applications (id, borrower_profile_id, created_by, amount_vnd,"
                    " term_months, status, exception_flag)"
                    " VALUES (:a, :p, :u, 1000000, 12, 'SUBMITTED', false)"
                ),
                {"a": app_id, "p": ids["profile"], "u": ids["user"]},
            )
        conn.execute(
            text(
                "INSERT INTO documents (id, application_id, doc_type, storage_key, mime_type,"
                " size_bytes, sha256, uploaded_by, uploaded_at)"
                " VALUES (:d, :a, 'national_id', 'k.jpg', 'image/jpeg', 1, 'h', :u, now())"
            ),
            {"d": ids["doc"], "a": ids["app"], "u": ids["user"]},
        )
        for action, target_type, target_id in [
            ("application.submit", "application", ids["app"]),
            ("document.upload", "document", ids["doc"]),
            ("application.read", "application", ids["other_app"]),
            ("auth.login", "user", ids["user"]),
            ("access.denied", "route:/users", None),
        ]:
            conn.execute(
                text(
                    "INSERT INTO audit_logs (id, actor_id, action, target_type, target_id,"
                    " created_at) VALUES (gen_random_uuid(), :u, :a, :t, :i, now())"
                ),
                {"u": ids["user"], "a": action, "t": target_type, "i": target_id},
            )

    command.upgrade(cfg, "head")

    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT action, application_id, seq FROM audit_logs ORDER BY seq")
        ).all()
    by_action = {action: (app_id, seq) for action, app_id, seq in rows}
    assert str(by_action["application.submit"][0]) == ids["app"]
    assert str(by_action["document.upload"][0]) == ids["app"]  # via the document's application
    assert str(by_action["application.read"][0]) == ids["other_app"]
    assert by_action["auth.login"][0] is None and by_action["access.denied"][0] is None
    assert all(seq is not None for _, seq in by_action.values())
    assert len({seq for _, seq in by_action.values()}) == len(rows)

    with pytest.raises(DBAPIError, match="append-only"), engine.begin() as conn:
        conn.execute(text("UPDATE audit_logs SET action = 'tampered'"))
    engine.dispose()


def test_lf016_downgrade_removes_the_locks_and_columns(scratch_url):
    cfg = alembic_config(scratch_url)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0005")

    engine = create_engine(scratch_url)
    with engine.begin() as conn:
        conn.execute(text("UPDATE audit_logs SET action = 'allowed-again'"))  # no trigger now
        columns = {
            row[0]
            for row in conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns"
                    " WHERE table_name = 'audit_logs'"
                )
            )
        }
    assert "seq" not in columns and "application_id" not in columns
    engine.dispose()
