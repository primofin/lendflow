"""LF-010 officer queue. Staff only; borrowers get 403 (audited)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import ClientIp, DbSession, Now, require_roles
from app.models.user import Role
from app.schemas.queue import QueuePageOut, QueueParams
from app.services import queue_service
from app.services.auth_service import AuthContext

router = APIRouter(prefix="/queue", tags=["queue"])

StaffAuth = Annotated[AuthContext, Depends(require_roles(Role.OFFICER, Role.SUPERVISOR))]


@router.get("")
def get_queue(
    params: Annotated[QueueParams, Query()],
    auth: StaffAuth,
    db: DbSession,
    clock: Now,
    ip: ClientIp,
) -> QueuePageOut:
    """LF-010: applications waiting for review, oldest first; filter by status or flag."""
    return queue_service.list_queue(db, viewer=auth.user, params=params, now=clock(), ip=ip)
