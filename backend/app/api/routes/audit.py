"""LF-016 audit log search. Read-only by design: there is no route that changes an entry."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession, require_roles
from app.models.user import Role
from app.schemas.audit import AuditEntryOut, AuditSearchParams
from app.services import audit_service
from app.services.auth_service import AuthContext

router = APIRouter(prefix="/audit-logs", tags=["audit"])

# Matrix: supervisors read everything, officers read their own actions; borrowers have no access.
AuditReaderAuth = Annotated[AuthContext, Depends(require_roles(Role.OFFICER, Role.SUPERVISOR))]


@router.get("")
def search_audit_log(
    params: Annotated[AuditSearchParams, Query()], auth: AuditReaderAuth, db: DbSession
) -> list[AuditEntryOut]:
    """LF-016: entries oldest first. Filter by application, actor, action and time range."""
    rows = audit_service.search(
        db,
        viewer=auth.user,
        application_id=params.application_id,
        actor_id=params.actor_id,
        action=params.action,
        created_from=params.created_from,
        created_to=params.created_to,
        limit=params.limit,
        offset=params.offset,
    )
    return [
        AuditEntryOut(
            seq=entry.seq,
            id=entry.id,
            created_at=entry.created_at,
            actor_id=entry.actor_id,
            actor_email=email,
            actor_role=role,
            action=entry.action,
            target_type=entry.target_type,
            target_id=entry.target_id,
            application_id=entry.application_id,
            ip_address=entry.ip_address,
        )
        for entry, email, role in rows
    ]
