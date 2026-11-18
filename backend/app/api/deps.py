"""Shared API dependencies: database, clock, client IP and current user (LF-001)."""

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.clock import Clock, get_clock
from app.core.db import get_db
from app.core.errors import NotAuthenticated
from app.services import auth_service
from app.services.auth_service import AuthContext

DbSession = Annotated[Session, Depends(get_db)]
Now = Annotated[Clock, Depends(get_clock)]

_bearer = HTTPBearer(auto_error=False)


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


ClientIp = Annotated[str | None, Depends(client_ip)]


def get_auth_context(
    db: DbSession,
    clock: Now,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthContext:
    if credentials is None:
        raise NotAuthenticated()
    return auth_service.authenticate_access(db, token=credentials.credentials, now=clock())


CurrentAuth = Annotated[AuthContext, Depends(get_auth_context)]
