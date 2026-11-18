"""Seed synthetic staff accounts for local development (LF-001/LF-002).

Staff cannot self-register; this script (or a supervisor, from LF-002) creates them.
Usage:  uv run python -m scripts.seed_users
Set SEED_PASSWORD to choose the password; otherwise a random one is generated and printed.
Idempotent: existing emails are left untouched.
"""

import os
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_engine
from app.core.security import hash_password
from app.models.user import Role, User

SEED_USERS = [
    ("officer@lendflow.example.com", Role.OFFICER),
    ("supervisor@lendflow.example.com", Role.SUPERVISOR),
]


def main() -> None:
    password = os.environ.get("SEED_PASSWORD") or secrets.token_urlsafe(12)
    with Session(get_engine()) as db:
        for email, role in SEED_USERS:
            if db.scalar(select(User.id).where(User.email == email)):
                print(f"exists   {email}")
                continue
            db.add(User(email=email, password_hash=hash_password(password), role=role))
            print(f"created  {email} ({role.value})")
        db.commit()
    if "SEED_PASSWORD" not in os.environ:
        print(f"password for new accounts: {password}")


if __name__ == "__main__":
    main()
