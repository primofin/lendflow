"""LF-001 registration, login with lockout, sessions with idle timeout and refresh rotation."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import get_settings
from app.core.errors import (
    AccountLocked,
    EmailAlreadyRegistered,
    InvalidCredentials,
    NotAuthenticated,
)
from app.models.session import AuthSession
from app.models.user import Role, User
from app.schemas.auth import TokenPair
from app.services import audit_service


@dataclass(frozen=True)
class AuthContext:
    user: User
    session: AuthSession


def normalise_email(email: str) -> str:
    return email.strip().lower()


def register(db: Session, *, email: str, password: str, now: datetime, ip: str | None) -> TokenPair:
    """Create a borrower account and log it in (LF-001 AC1, AC2)."""
    email = normalise_email(email)
    if db.scalar(select(User.id).where(User.email == email)):
        raise EmailAlreadyRegistered()
    user = User(email=email, password_hash=security.hash_password(password), role=Role.BORROWER)
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:  # concurrent registration with the same email
        db.rollback()
        raise EmailAlreadyRegistered() from exc
    audit_service.record(
        db,
        action="auth.register",
        now=now,
        actor_id=user.id,
        target_type="user",
        target_id=user.id,
        ip_address=ip,
    )
    tokens = _start_session(db, user, now)
    db.commit()
    return tokens


def login(db: Session, *, email: str, password: str, now: datetime, ip: str | None) -> TokenPair:
    """Verify credentials; lock after repeated failures (LF-001 AC3)."""
    user = db.scalar(select(User).where(User.email == normalise_email(email)).with_for_update())
    if user is None:
        security.burn_password_check(password)
        raise InvalidCredentials()

    if user.locked_until and user.locked_until > now:
        _audit_user(db, user, "auth.login_while_locked", now, ip)
        db.commit()
        raise AccountLocked(_locked_message())

    if not security.verify_password(password, user.password_hash) or not user.is_active:
        _register_failure(db, user, now, ip)
        db.commit()
        if user.locked_until:
            raise AccountLocked(_locked_message())
        raise InvalidCredentials()

    user.failed_login_count = 0
    user.locked_until = None
    _audit_user(db, user, "auth.login", now, ip)
    tokens = _start_session(db, user, now)
    db.commit()
    return tokens


def refresh(db: Session, *, refresh_token: str, now: datetime, ip: str | None) -> TokenPair:
    """Rotate the refresh token; the presented one stops working (LF-001 notes).

    Presenting the token that was just rotated out means two parties hold it, so the
    whole session is revoked (OAuth refresh-token reuse detection).
    """
    token_hash = security.hash_refresh_token(refresh_token)
    session = db.scalar(
        select(AuthSession).where(AuthSession.refresh_token_hash == token_hash).with_for_update()
    )
    if session is None:
        _revoke_on_reuse(db, token_hash, now, ip)
        raise NotAuthenticated()
    _ensure_session_usable(db, session, now)
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise NotAuthenticated()

    new_token = security.new_refresh_token()
    session.previous_refresh_token_hash = token_hash
    session.refresh_token_hash = security.hash_refresh_token(new_token)
    session.last_activity_at = now
    db.commit()
    return TokenPair(
        access_token=security.create_access_token(user.id, session.id), refresh_token=new_token
    )


def authenticate_access(db: Session, *, token: str, now: datetime) -> AuthContext:
    """Resolve a bearer token to an active user and live session; records activity."""
    try:
        claims = security.decode_access_token(token)
    except security.TokenError as exc:
        raise NotAuthenticated() from exc
    session = db.get(AuthSession, claims.session_id)
    if session is None or session.user_id != claims.user_id:
        raise NotAuthenticated()
    _ensure_session_usable(db, session, now)
    user = db.get(User, claims.user_id)
    if user is None or not user.is_active:
        raise NotAuthenticated()
    session.last_activity_at = now
    db.commit()
    return AuthContext(user=user, session=session)


def logout(db: Session, *, ctx: AuthContext, now: datetime, ip: str | None) -> None:
    ctx.session.revoked_at = now
    _audit_user(db, ctx.user, "auth.logout", now, ip)
    db.commit()


# --- helpers ----------------------------------------------------------------


def _start_session(db: Session, user: User, now: datetime) -> TokenPair:
    settings = get_settings()
    refresh_token = security.new_refresh_token()
    session = AuthSession(
        user_id=user.id,
        refresh_token_hash=security.hash_refresh_token(refresh_token),
        last_activity_at=now,
        expires_at=now + timedelta(days=settings.refresh_token_ttl_days),
    )
    db.add(session)
    db.flush()
    return TokenPair(
        access_token=security.create_access_token(user.id, session.id),
        refresh_token=refresh_token,
    )


def _ensure_session_usable(db: Session, session: AuthSession, now: datetime) -> None:
    """Reject revoked, expired or idle sessions (LF-001 AC4: 30-minute idle logout)."""
    idle_limit = timedelta(minutes=get_settings().session_idle_timeout_minutes)
    if session.revoked_at is not None or session.expires_at <= now:
        raise NotAuthenticated()
    if now - session.last_activity_at > idle_limit:
        session.revoked_at = now
        db.commit()
        raise NotAuthenticated("Session expired after inactivity. Log in again.")


def _revoke_on_reuse(db: Session, token_hash: str, now: datetime, ip: str | None) -> None:
    session = db.scalar(
        select(AuthSession)
        .where(AuthSession.previous_refresh_token_hash == token_hash)
        .with_for_update()
    )
    if session is None or session.revoked_at is not None:
        return
    session.revoked_at = now
    audit_service.record(
        db,
        action="auth.refresh_reuse",
        now=now,
        actor_id=session.user_id,
        target_type="auth_session",
        target_id=session.id,
        ip_address=ip,
    )
    db.commit()


def _register_failure(db: Session, user: User, now: datetime, ip: str | None) -> None:
    settings = get_settings()
    user.failed_login_count += 1
    _audit_user(db, user, "auth.login_failed", now, ip)
    if user.failed_login_count >= settings.login_max_failures:
        user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
        user.failed_login_count = 0
        _audit_user(db, user, "auth.lockout", now, ip)


def _locked_message() -> str:
    minutes = get_settings().lockout_minutes
    return (
        f"Too many failed attempts. The account is locked for {minutes} minutes; try again later."
    )


def _audit_user(db: Session, user: User, action: str, now: datetime, ip: str | None) -> None:
    audit_service.record(
        db,
        action=action,
        now=now,
        actor_id=user.id,
        target_type="user",
        target_id=user.id,
        ip_address=ip,
    )


__all__ = ["AuthContext", "authenticate_access", "login", "logout", "refresh", "register"]
