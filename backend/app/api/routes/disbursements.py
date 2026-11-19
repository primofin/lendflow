"""LF-020 disbursement and the simulated face-match step (staff only)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import ClientIp, DbSession, Now, require_roles
from app.models.user import Role
from app.schemas.disbursement import (
    DisbursementIn,
    DisbursementOut,
    DisbursementStatusOut,
    FaceMatchIn,
    FaceMatchOut,
)
from app.services import disbursement_service
from app.services.auth_service import AuthContext

router = APIRouter(prefix="/applications", tags=["disbursement"])

StaffAuth = Annotated[AuthContext, Depends(require_roles(Role.OFFICER, Role.SUPERVISOR))]


@router.get("/{application_id}/disbursement")
def get_disbursement(
    application_id: uuid.UUID, auth: StaffAuth, db: DbSession, clock: Now, ip: ClientIp
) -> DisbursementStatusOut:
    """LF-020: whether the loan is disbursed and whether a face match is required."""
    return disbursement_service.status(
        db, user=auth.user, application_id=application_id, now=clock(), ip=ip
    )


@router.post("/{application_id}/face-match", status_code=status.HTTP_201_CREATED)
def face_match(
    application_id: uuid.UUID,
    body: FaceMatchIn,
    auth: StaffAuth,
    db: DbSession,
    clock: Now,
    ip: ClientIp,
) -> FaceMatchOut:
    """LF-020: simulated face match (C-07). Returns a single-use, short-lived token."""
    return disbursement_service.simulate_face_match(
        db, user=auth.user, application_id=application_id, data=body, now=clock(), ip=ip
    )


@router.post("/{application_id}/disbursement", status_code=status.HTTP_201_CREATED)
def disburse(
    application_id: uuid.UUID,
    body: DisbursementIn,
    auth: StaffAuth,
    db: DbSession,
    clock: Now,
    ip: ClientIp,
) -> DisbursementOut:
    """LF-020: pay out an approved loan; above the threshold a passed face match is required."""
    return disbursement_service.disburse(
        db, user=auth.user, application_id=application_id, data=body, now=clock(), ip=ip
    )
