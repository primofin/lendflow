"""Shared fixtures: real Postgres test DB, per-test transaction rollback, fake clock."""

import uuid
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from app.core.clock import get_clock, utcnow
from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import hash_password
from app.main import create_app
from app.models.user import Role, User

TEST_PASSWORD = "test-password-1"


class FakeClock:
    """Starts at real 'now' so JWT expiry (checked against wall time) stays consistent."""

    def __init__(self) -> None:
        self.now = utcnow()

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs: float) -> None:
        self.now += timedelta(**kwargs)


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    url = get_settings().test_database_url
    eng = create_engine(url)
    with eng.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    cfg = Config("alembic.ini")
    cfg.attributes["database_url"] = url
    command.upgrade(cfg, "head")
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    conn = engine.connect()
    outer = conn.begin()
    session = Session(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    yield session
    session.close()
    outer.rollback()
    conn.close()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def client(db: Session, clock: FakeClock) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_clock] = lambda: clock
    with TestClient(app) as c:
        yield c


MakeUser = Callable[..., tuple[User, dict[str, str]]]


@pytest.fixture
def make_user(client: TestClient, db: Session) -> MakeUser:
    """Create a user with a role, log in through the API, return (user, auth headers)."""

    def _make(role: Role = Role.BORROWER, *, active: bool = True) -> tuple[User, dict[str, str]]:
        email = f"{role.value}-{uuid.uuid4().hex[:8]}@example.com"
        user = User(email=email, password_hash=hash_password(TEST_PASSWORD), role=role)
        db.add(user)
        db.commit()
        tokens = client.post("/auth/login", json={"email": email, "password": TEST_PASSWORD})
        headers = {"Authorization": f"Bearer {tokens.json()['access_token']}"}
        if not active:
            user.is_active = False
            db.commit()
        return user, headers

    return _make


@pytest.fixture(autouse=True)
def storage_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """LF-005: every test writes uploads into its own temporary folder, never the project's."""
    folder = tmp_path / "storage"
    monkeypatch.setattr(get_settings(), "storage_dir", folder)
    return folder
