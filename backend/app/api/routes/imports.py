"""LF-013 CSV bulk import. Officers and supervisors only (docs/01 permission matrix)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, UploadFile, status

from app.api.deps import ClientIp, DbSession, Now, require_roles
from app.core.config import get_settings
from app.models.user import Role
from app.schemas.import_ import ImportResultOut
from app.services import import_service
from app.services.auth_service import AuthContext

router = APIRouter(prefix="/imports", tags=["imports"])

StaffAuth = Annotated[AuthContext, Depends(require_roles(Role.OFFICER, Role.SUPERVISOR))]


@router.get("/applications/template")
def download_template(auth: StaffAuth) -> Response:
    """LF-013: the column names and one synthetic example row."""
    return Response(
        import_service.TEMPLATE_CSV,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="applications-template.csv"'},
    )


@router.post("/applications", status_code=status.HTTP_201_CREATED)
def import_applications(
    file: UploadFile, auth: StaffAuth, db: DbSession, clock: Now, ip: ClientIp
) -> ImportResultOut:
    """LF-013: valid rows become DRAFT applications; the result lists skipped and invalid rows."""
    # One byte past the limit, so the service can tell "exactly at" from "over".
    data = file.file.read(get_settings().import_max_bytes + 1)
    return import_service.import_applications(
        db, user=auth.user, filename=file.filename, data=data, now=clock(), ip=ip
    )
