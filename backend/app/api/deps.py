"""Shared API dependencies: database, clock, client IP and current user (LF-001)."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.clock import Clock, get_clock
from app.core.db import get_db
from app.core.errors import Forbidden, NotAuthenticated
from app.models.user import Role
from app.services import audit_service, auth_service
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


def require_roles(*allowed: Role) -> Callable[..., AuthContext]:
    """LF-002: the caller must hold one of `allowed`. Refusals return 403 and are audited."""

    def _check(
        auth: CurrentAuth, request: Request, db: DbSession, clock: Now, ip: ClientIp
    ) -> AuthContext:
        if auth.user.role in allowed:
            return auth
        route_path = getattr(request.scope.get("route"), "path", "unknown")
        audit_service.record(
            db,
            action="access.denied",
            now=clock(),
            actor_id=auth.user.id,
            target_type=f"route:{route_path}"[:64],
            ip_address=ip,
        )
        db.commit()
        raise Forbidden()

    return _check


SupervisorAuth = Annotated[AuthContext, Depends(require_roles(Role.SUPERVISOR))]
BorrowerAuth = Annotated[AuthContext, Depends(require_roles(Role.BORROWER))]
