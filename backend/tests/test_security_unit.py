"""Unit tests for app.core.security (LF-001)."""

import uuid
from datetime import timedelta

import jwt
import pytest

from app.core.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    new_refresh_token,
    verify_password,
)


def test_lf001_hash_and_verify_password_roundtrip():
    hashed = hash_password("correct-horse-battery")

    assert verify_password("correct-horse-battery", hashed)
    assert not verify_password("wrong-password-1", hashed)


def test_lf001_access_token_roundtrip():
    user_id, session_id = uuid.uuid4(), uuid.uuid4()

    claims = decode_access_token(create_access_token(user_id, session_id))

    assert claims.user_id == user_id
    assert claims.session_id == session_id


def test_lf001_expired_access_token_rejected():
    token = create_access_token(uuid.uuid4(), uuid.uuid4(), ttl=timedelta(seconds=-1))

    with pytest.raises(TokenError):
        decode_access_token(token)


def test_lf001_token_signed_with_other_key_rejected():
    forged = jwt.encode({"sub": str(uuid.uuid4()), "sid": str(uuid.uuid4())}, "x" * 32)

    with pytest.raises(TokenError):
        decode_access_token(forged)


def test_lf001_refresh_token_is_random_and_hash_is_stable():
    a, b = new_refresh_token(), new_refresh_token()

    assert a != b
    assert hash_refresh_token(a) == hash_refresh_token(a)
    assert hash_refresh_token(a) != a
