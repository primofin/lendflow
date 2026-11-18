"""LF-005 document upload, listing and download.

Order of checks on upload: who you are, which application, whether it still accepts documents,
then the file itself (empty, size, real type), then duplicates and limits. The file is written
to disk only after every check passes, and removed again if recording it fails.
"""

import hashlib
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import (
    Conflict,
    NotFound,
    PayloadTooLarge,
    UnprocessableEntity,
    UnsupportedMediaType,
)
from app.core.permissions import STAFF_ROLES
from app.models.application import Application, ApplicationStatus
from app.models.document import DocType, Document
from app.models.user import User
from app.schemas.document import UploadNoticeOut
from app.services import application_service, audit_service, file_storage, queue_service
from app.services.file_sniffing import ALLOWED_MIME_TYPES, EXTENSIONS, detect_mime

# IN_REVIEW stays open so a borrower can still add optional documents once the file is queued
# (LF-010); NEEDS_INFO is where the borrower answers a request for information (LF-012).
UPLOADABLE_STATUSES = frozenset(
    {
        ApplicationStatus.SUBMITTED.value,
        ApplicationStatus.IN_REVIEW.value,
        ApplicationStatus.NEEDS_INFO.value,
    }
)

SYNTHETIC_NOTICE = (
    "Demo only: upload synthetic or non-real documents. Do not upload real identity "
    "documents, bank statements or any other real personal data."
)


def upload_notice() -> UploadNoticeOut:
    return UploadNoticeOut(
        notice=SYNTHETIC_NOTICE,
        allowed_types=list(ALLOWED_MIME_TYPES),
        max_size_mb=get_settings().max_upload_bytes // (1024 * 1024),
    )


def upload(
    db: Session,
    *,
    user: User,
    application_id: uuid.UUID,
    doc_type: DocType,
    data: bytes,
    now: datetime,
    ip: str | None,
) -> tuple[Document, bool]:
    """Store a document. Returns (document, created); created is False for a retried upload."""
    settings = get_settings()
    application = application_service.get_for_user(
        db, user=user, application_id=application_id, now=now, ip=ip, audit_read=False
    )
    if application.status not in UPLOADABLE_STATUSES:
        raise Conflict("Documents can no longer be added to this application.")

    if not data:
        raise UnprocessableEntity("The file is empty. Choose a file that has content and retry.")
    if len(data) > settings.max_upload_bytes:
        limit_mb = settings.max_upload_bytes // (1024 * 1024)
        raise PayloadTooLarge(
            f"This file is larger than the {limit_mb} MB limit. Upload a smaller scan or photo "
            "(lower the photo quality or compress the PDF)."
        )
    mime = detect_mime(data)
    if mime is None:
        raise UnsupportedMediaType("Unsupported file type. Upload a JPG, PNG or PDF.")

    sha256 = hashlib.sha256(data).hexdigest()
    existing = _find_duplicate(db, application, doc_type, sha256)
    if existing is not None:
        return existing, False

    count = db.scalar(
        select(func.count()).select_from(Document).where(Document.application_id == application.id)
    )
    if count >= settings.max_documents_per_application:
        raise Conflict(
            f"This application already has {settings.max_documents_per_application} documents, "
            "the maximum. Contact your loan officer to add more."
        )

    key = f"{uuid.uuid4().hex}{EXTENSIONS[mime]}"
    file_storage.save(key, data)
    try:
        document = Document(
            application_id=application.id,
            doc_type=doc_type.value,
            storage_key=key,
            mime_type=mime,
            size_bytes=len(data),
            sha256=sha256,
            uploaded_by=user.id,
            uploaded_at=now,
        )
        db.add(document)
        db.flush()
        audit_service.record(
            db,
            action="document.upload",
            now=now,
            actor_id=user.id,
            target_type="document",
            target_id=document.id,
            application_id=application.id,
            ip_address=ip,
        )
        queue_service.promote_if_ready(db, application, actor_id=user.id, now=now, ip=ip)
        db.commit()
    except IntegrityError:  # a concurrent retry stored the same content first
        db.rollback()
        file_storage.delete(key)
        existing = _find_duplicate(db, application, doc_type, sha256)
        if existing is None:
            raise
        return existing, False
    except Exception:
        db.rollback()
        file_storage.delete(key)
        raise
    return document, True


def list_documents(
    db: Session, *, user: User, application_id: uuid.UUID, now: datetime, ip: str | None
) -> list[Document]:
    application = application_service.get_for_user(
        db, user=user, application_id=application_id, now=now, ip=ip, audit_read=False
    )
    documents = list(
        db.scalars(
            select(Document)
            .where(Document.application_id == application.id)
            .order_by(Document.uploaded_at, Document.id)
        )
    )
    if user.role in STAFF_ROLES:  # RBAC rule 4: staff reads of personal data are logged
        _audit(db, user, "document.list", "application", application.id, application.id, now, ip)
        db.commit()
    return documents


def get_file(
    db: Session,
    *,
    user: User,
    application_id: uuid.UUID,
    document_id: uuid.UUID,
    now: datetime,
    ip: str | None,
) -> tuple[Document, bytes]:
    application = application_service.get_for_user(
        db, user=user, application_id=application_id, now=now, ip=ip, audit_read=False
    )
    document = db.get(Document, document_id)
    if document is None or document.application_id != application.id:
        raise NotFound("Document not found")
    try:
        content = file_storage.read(document.storage_key)
    except FileNotFoundError as exc:
        raise NotFound("The stored file is missing. Contact support.") from exc
    if user.role in STAFF_ROLES:
        _audit(db, user, "document.download", "document", document.id, application.id, now, ip)
        db.commit()
    return document, content


def _find_duplicate(
    db: Session, application: Application, doc_type: DocType, sha256: str
) -> Document | None:
    return db.scalar(
        select(Document).where(
            Document.application_id == application.id,
            Document.doc_type == doc_type.value,
            Document.sha256 == sha256,
        )
    )


def _audit(
    db: Session,
    user: User,
    action: str,
    target_type: str,
    target_id: uuid.UUID,
    application_id: uuid.UUID,
    now: datetime,
    ip: str | None,
) -> None:
    audit_service.record(
        db,
        action=action,
        now=now,
        actor_id=user.id,
        target_type=target_type,
        target_id=target_id,
        application_id=application_id,
        ip_address=ip,
    )
