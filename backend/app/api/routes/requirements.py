"""LF-007 document requirements, checklist and exceptions."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import ClientIp, CurrentAuth, DbSession, Now, require_roles
from app.models.user import Role
from app.schemas.requirements import ChecklistOut, ExceptionDeclareIn, PanelOut
from app.services import application_service, exception_service, requirements_service
from app.services.auth_service import AuthContext

router = APIRouter(tags=["requirements"])

# Matrix: income-type rules are staff-readable; only officers declare exceptions (LF-007 AC3).
StaffAuth = Annotated[AuthContext, Depends(require_roles(Role.OFFICER, Role.SUPERVISOR))]
OfficerAuth = Annotated[AuthContext, Depends(require_roles(Role.OFFICER))]


@router.get("/income-types/{income_type}/requirements")
def requirements_panel(income_type: str, auth: StaffAuth, db: DbSession) -> PanelOut:
    """LF-007: mandatory and optional documents for an income type (BR-06)."""
    return requirements_service.panel(db, income_type)


@router.get("/applications/{application_id}/checklist")
def application_checklist(
    application_id: uuid.UUID, auth: CurrentAuth, db: DbSession, clock: Now, ip: ClientIp
) -> ChecklistOut:
    """LF-007: what is satisfied, waived or missing. Owner and staff only; staff reads audited."""
    application = application_service.get_for_user(
        db, user=auth.user, application_id=application_id, now=clock(), ip=ip
    )
    return requirements_service.checklist(db, application)


@router.post("/applications/{application_id}/exceptions", status_code=status.HTTP_201_CREATED)
def declare_exception(
    application_id: uuid.UUID,
    body: ExceptionDeclareIn,
    auth: OfficerAuth,
    db: DbSession,
    clock: Now,
    ip: ClientIp,
    response: Response,
) -> ChecklistOut:
    """LF-007: "No <document> available". Flags the file and assigns a supervisor."""
    application, created = exception_service.declare(
        db,
        officer=auth.user,
        application_id=application_id,
        requirement_id=body.requirement_id,
        now=clock(),
        ip=ip,
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    return requirements_service.checklist(db, application)
