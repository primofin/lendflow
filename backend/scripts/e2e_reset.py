"""Reset the TEST database for the browser (Playwright) tests and seed fixed staff accounts.

Usage: uv run python -m scripts.e2e_reset
Refuses to run unless the database name ends in "_test", so it can never wipe a dev database.
Staff password comes from E2E_PASSWORD (default: a fixed demo value for synthetic accounts).
"""

import os

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.user import Role, User

STAFF = [
    ("e2e-officer@lendflow.example.com", Role.OFFICER),
    ("e2e-supervisor@lendflow.example.com", Role.SUPERVISOR),
]


def main() -> None:
    url = get_settings().test_database_url
    name = make_url(url).database or ""
    if not name.endswith("_test"):
        raise SystemExit(f"Refusing to reset '{name}': only databases ending in _test are reset")

    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    cfg = Config("alembic.ini")
    cfg.attributes["database_url"] = url
    command.upgrade(cfg, "head")

    password = os.environ.get("E2E_PASSWORD", "e2e-password-123")
    with Session(engine) as db:
        for email, role in STAFF:
            db.add(User(email=email, password_hash=hash_password(password), role=role))
        db.commit()
    engine.dispose()
    print(f"reset {name}; staff accounts: {', '.join(e for e, _ in STAFF)}")


if __name__ == "__main__":
    main()
