"""LF-005 document upload, list and download. Authorization is enforced here and in the service."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Response, UploadFile, status

from app.api.deps import ClientIp, CurrentAuth, DbSession, Now, require_roles
from app.core.config import get_settings
from app.models.document import DocType
from app.models.user import Role
from app.schemas.document import DocumentOut, UploadNoticeOut
from app.services import document_service
from app.services.auth_service import AuthContext
from app.services.file_sniffing import EXTENSIONS

router = APIRouter(tags=["documents"])

# Matrix: borrowers (own application) and officers upload; supervisors view only.
UploaderAuth = Annotated[AuthContext, Depends(require_roles(Role.BORROWER, Role.OFFICER))]


@router.get("/documents/notice")
def upload_notice() -> UploadNoticeOut:
    """LF-005 / BR-24: shown on the upload screen. Public."""
    return document_service.upload_notice()


@router.post("/applications/{application_id}/documents", status_code=status.HTTP_201_CREATED)
def upload_document(
    application_id: uuid.UUID,
    doc_type: Annotated[DocType, Form()],
    file: UploadFile,
    auth: UploaderAuth,
    db: DbSession,
    clock: Now,
    ip: ClientIp,
    response: Response,
) -> DocumentOut:
    """LF-005: JPG, PNG or PDF up to 5 MB. Re-sending the same file returns it (200), not a copy."""
    # Read one byte past the limit so the service can tell "exactly at" from "over" without
    # ever holding more than limit + 1 bytes in memory.
    data = file.file.read(get_settings().max_upload_bytes + 1)
    document, created = document_service.upload(
        db,
        user=auth.user,
        application_id=application_id,
        doc_type=doc_type,
        data=data,
        now=clock(),
        ip=ip,
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    return DocumentOut.model_validate(document)


@router.get("/applications/{application_id}/documents")
def list_documents(
    application_id: uuid.UUID, auth: CurrentAuth, db: DbSession, clock: Now, ip: ClientIp
) -> list[DocumentOut]:
    """LF-005: documents with type and upload time. Staff reads are audited."""
    documents = document_service.list_documents(
        db, user=auth.user, application_id=application_id, now=clock(), ip=ip
    )
    return [DocumentOut.model_validate(d) for d in documents]


@router.get("/applications/{application_id}/documents/{document_id}/file")
def download_document(
    application_id: uuid.UUID,
    document_id: uuid.UUID,
    auth: CurrentAuth,
    db: DbSession,
    clock: Now,
    ip: ClientIp,
) -> Response:
    """LF-005: the stored file, as an attachment the browser cannot sniff or run. Staff audited."""
    document, content = document_service.get_file(
        db,
        user=auth.user,
        application_id=application_id,
        document_id=document_id,
        now=clock(),
        ip=ip,
    )
    return Response(
        content=content,
        media_type=document.mime_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="document-{document.id}{EXTENSIONS[document.mime_type]}"'
            ),
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
        },
    )
