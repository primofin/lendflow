"""LF-002 user management: supervisors create users and assign roles."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import Conflict, EmailAlreadyRegistered, NotFound
from app.core.security import hash_password
from app.models.user import Role, User
from app.services import audit_service
from app.services.auth_service import normalise_email


def list_users(db: Session) -> Sequence[User]:
    return db.scalars(select(User).order_by(User.created_at, User.email)).all()


def create_user(
    db: Session,
    *,
    actor: User,
    email: str,
    password: str,
    role: Role,
    now: datetime,
    ip: str | None,
) -> User:
    email = normalise_email(email)
    if db.scalar(select(User.id).where(User.email == email)):
        raise EmailAlreadyRegistered()
    user = User(email=email, password_hash=hash_password(password), role=role)
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:  # concurrent creation with the same email
        db.rollback()
        raise EmailAlreadyRegistered() from exc
    _audit(db, actor, "user.create", user.id, now, ip)
    db.commit()
    return user


def change_role(
    db: Session,
    *,
    actor: User,
    user_id: uuid.UUID,
    role: Role,
    now: datetime,
    ip: str | None,
) -> User:
    target = db.get(User, user_id, with_for_update=True)
    if target is None:
        raise NotFound("User not found")
    if target.id == actor.id:
        # Prevents a supervisor accidentally removing the last supervisor (themselves).
        raise Conflict("You cannot change your own role. Ask another supervisor.")
    target.role = role
    _audit(db, actor, "user.role_change", target.id, now, ip)
    db.commit()
    return target


def _audit(
    db: Session, actor: User, action: str, target_id: uuid.UUID, now: datetime, ip: str | None
) -> None:
    audit_service.record(
        db,
        action=action,
        now=now,
        actor_id=actor.id,
        target_type="user",
        target_id=target_id,
        ip_address=ip,
    )
