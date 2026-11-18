"""Password hashing and token primitives (LF-001)."""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

_hasher = PasswordHash.recommended()  # argon2id
# Used to spend the same time verifying when the email is unknown (no user enumeration by timing).
_DUMMY_HASH = _hasher.hash("lendflow-timing-equaliser")


class TokenError(Exception):
    """Raised when an access token is missing, malformed, expired or forged."""


@dataclass(frozen=True)
class AccessClaims:
    user_id: uuid.UUID
    session_id: uuid.UUID


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _hasher.verify(password, password_hash)


def burn_password_check(password: str) -> None:
    _hasher.verify(password, _DUMMY_HASH)


def create_access_token(
    user_id: uuid.UUID, session_id: uuid.UUID, ttl: timedelta | None = None
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    ttl = ttl if ttl is not None else timedelta(minutes=settings.access_token_ttl_minutes)
    payload = {"sub": str(user_id), "sid": str(session_id), "iat": now, "exp": now + ttl}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> AccessClaims:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "sid", "exp"]},
        )
        return AccessClaims(uuid.UUID(payload["sub"]), uuid.UUID(payload["sid"]))
    except (jwt.PyJWTError, ValueError) as exc:
        raise TokenError("Invalid or expired access token") from exc


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    # Refresh tokens are high-entropy random values, so a fast hash is sufficient.
    return hashlib.sha256(token.encode()).hexdigest()
