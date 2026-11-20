"""Create or refresh the least-privilege database role the running API uses (D-005).

Run as the database OWNER (the role that runs migrations), after every `alembic upgrade head`:

    APP_DB_PASSWORD=... uv run python -m scripts.provision_app_role

The API role may read and write the tables, but may only SELECT and INSERT on the append-only
tables (audit_logs, decisions), so a compromised API process cannot rewrite history even by
dropping the triggers' protection (it cannot drop triggers either: it owns nothing).
Idempotent. Point the API's DATABASE_URL at this role and keep MIGRATION_DATABASE_URL on the owner.
"""

import os
import re
import sys

import psycopg
from psycopg import sql

from app.core.config import get_settings

APPEND_ONLY_TABLES = ("audit_logs", "decisions")
_ROLE_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


def provision(conn: psycopg.Connection, role: str, password: str) -> None:
    if not _ROLE_RE.fullmatch(role):
        raise ValueError("APP_DB_ROLE must be lowercase letters, digits and underscores")
    if len(password) < 16:
        raise ValueError("APP_DB_PASSWORD must be at least 16 characters")
    who = sql.Identifier(role)
    owner = conn.execute("SELECT current_user").fetchone()
    assert owner is not None  # noqa: S101
    exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone()
    verb = "ALTER" if exists else "CREATE"
    conn.execute(
        sql.SQL(verb + " ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {}").format(
            who, sql.Literal(password)
        )
    )
    db = conn.execute("SELECT current_database()").fetchone()
    assert db is not None  # noqa: S101
    conn.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(db[0]), who))
    conn.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(who))
    conn.execute(
        sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {}").format(
            who
        )
    )
    conn.execute(sql.SQL("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {}").format(who))
    for table in APPEND_ONLY_TABLES:
        conn.execute(
            sql.SQL("REVOKE UPDATE, DELETE, TRUNCATE ON {} FROM {}").format(
                sql.Identifier(table), who
            )
        )
    # Tables created by later migrations get the same default grants for this role.
    conn.execute(
        sql.SQL(
            "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public "
            "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}"
        ).format(sql.Identifier(owner[0]), who)
    )
    conn.execute(
        sql.SQL(
            "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA public "
            "GRANT USAGE, SELECT ON SEQUENCES TO {}"
        ).format(sql.Identifier(owner[0]), who)
    )


def main() -> None:
    password = os.environ.get("APP_DB_PASSWORD")
    if not password:
        sys.exit("Set APP_DB_PASSWORD (at least 16 characters) for the new role.")
    role = os.environ.get("APP_DB_ROLE", "lendflow_app")
    url = os.environ.get("MIGRATION_DATABASE_URL") or get_settings().database_url
    with psycopg.connect(url.replace("postgresql+psycopg://", "postgresql://")) as conn:
        provision(conn, role, password)
    print(f"role {role} provisioned (SELECT/INSERT only on {', '.join(APPEND_ONLY_TABLES)})")


if __name__ == "__main__":
    main()
