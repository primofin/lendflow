"""Application endpoints. LF-002: read with ownership check; LF-004 adds create/edit."""

import uuid

from fastapi import APIRouter

from app.api.deps import ClientIp, CurrentAuth, DbSession, Now
from app.schemas.application import ApplicationOut
from app.services import application_service

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("/{application_id}")
def get_application(
    application_id: uuid.UUID, auth: CurrentAuth, db: DbSession, clock: Now, ip: ClientIp
) -> ApplicationOut:
    """LF-002: borrowers see only their own; staff reads are audited."""
    application = application_service.get_for_user(
        db, user=auth.user, application_id=application_id, now=clock(), ip=ip
    )
    return ApplicationOut.model_validate(application)
