"""Application endpoints. LF-002: read with ownership check; LF-004: submit with consent."""

import uuid

from fastapi import APIRouter, status

from app.api.deps import BorrowerAuth, ClientIp, CurrentAuth, DbSession, Now
from app.schemas.application import ApplicationOut, ApplicationSubmitIn
from app.services import application_service

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("", status_code=status.HTTP_201_CREATED)
def submit_application(
    body: ApplicationSubmitIn, auth: BorrowerAuth, db: DbSession, clock: Now, ip: ClientIp
) -> ApplicationOut:
    """LF-004: borrower submits with consent; nothing is saved unless every rule passes."""
    application = application_service.submit(db, user=auth.user, data=body, now=clock(), ip=ip)
    return ApplicationOut.model_validate(application)


@router.get("/{application_id}")
def get_application(
    application_id: uuid.UUID, auth: CurrentAuth, db: DbSession, clock: Now, ip: ClientIp
) -> ApplicationOut:
    """LF-002: borrowers see only their own; staff reads are audited."""
    application = application_service.get_for_user(
        db, user=auth.user, application_id=application_id, now=clock(), ip=ip
    )
    return ApplicationOut.model_validate(application)
