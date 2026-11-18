"""LF-011 reason codes for rejections. The decision endpoints live under /applications."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, require_roles
from app.models.user import Role
from app.schemas.decision import ReasonCodeOut
from app.services import decision_service
from app.services.auth_service import AuthContext

router = APIRouter(tags=["decisions"])

StaffAuth = Annotated[AuthContext, Depends(require_roles(Role.OFFICER, Role.SUPERVISOR))]


@router.get("/reason-codes")
def list_reason_codes(auth: StaffAuth, db: DbSession) -> list[ReasonCodeOut]:
    """LF-011: the rejection reasons a decision may use (illustrative list, open item Q6)."""
    return [
        ReasonCodeOut(code=c.code, label=c.label) for c in decision_service.list_reason_codes(db)
    ]
