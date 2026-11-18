"""LF-018 data-subject rights. Borrowers act on their own data only; supervisors see requests."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.api.deps import BorrowerAuth, ClientIp, DbSession, Now, SupervisorAuth
from app.schemas.data_rights import DeletionRequestAdminOut, DeletionRequestOut, MyDataOut
from app.services import data_rights_service

router = APIRouter(tags=["data-rights"])


@router.get("/me/data")
def get_my_data(auth: BorrowerAuth, db: DbSession) -> MyDataOut:
    """LF-018: all personal data held about the caller, the purposes and any deletion request."""
    return data_rights_service.my_data(db, user=auth.user)


@router.get("/me/data/export")
def export_my_data(auth: BorrowerAuth, db: DbSession, clock: Now, ip: ClientIp) -> JSONResponse:
    """LF-018: the same data as a downloadable JSON file."""
    data = data_rights_service.export(db, user=auth.user, now=clock(), ip=ip)
    return JSONResponse(
        data.model_dump(mode="json"),
        headers={"Content-Disposition": 'attachment; filename="my-lendflow-data.json"'},
    )


@router.post("/me/data/deletion-request", status_code=status.HTTP_201_CREATED)
def request_deletion(
    auth: BorrowerAuth, db: DbSession, clock: Now, ip: ClientIp
) -> DeletionRequestOut:
    """LF-018: record a deletion request with a due date; says what must be retained."""
    return data_rights_service.request_deletion(db, user=auth.user, now=clock(), ip=ip)


@router.get("/data-requests")
def list_data_requests(
    auth: SupervisorAuth, db: DbSession, clock: Now
) -> list[DeletionRequestAdminOut]:
    """LF-018: open and resolved deletion requests with their due dates."""
    return data_rights_service.list_requests(db, now=clock())
