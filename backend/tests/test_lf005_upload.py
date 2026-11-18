"""LF-005 Upload documents. Acceptance criteria: docs/04; rules BR-23, BR-24, C-12."""

import hashlib
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.user import Role

from .test_lf004_submit import submit

MB = 1024 * 1024
JPEG = b"\xff\xd8\xff\xe0" + b"\x01" * 200
PNG = b"\x89PNG\r\n\x1a\n" + b"\x02" * 200
PDF = b"%PDF-1.7\n" + b"\x03" * 200


def stored_files(storage_dir: Path) -> list[Path]:
    return [p for p in storage_dir.rglob("*") if p.is_file()] if storage_dir.exists() else []


def doc_count(db) -> int:
    return db.scalar(select(func.count()).select_from(Document))


def new_application(client, make_user):
    owner, headers = make_user(Role.BORROWER)
    response = submit(client, headers)
    assert response.status_code == 201
    return owner, headers, response.json()["id"]


def upload(
    client,
    headers,
    application_id,
    content=JPEG,
    *,
    doc_type="national_id",
    filename="scan.jpg",
    content_type="image/jpeg",
):
    return client.post(
        f"/applications/{application_id}/documents",
        headers=headers,
        data={"doc_type": doc_type},
        files={"file": (filename, content, content_type)},
    )


def audit_actions(db):
    return db.scalars(select(AuditLog.action)).all()


# --- Notice (AC3, BR-24) -----------------------------------------------------------


def test_lf005_notice_warns_synthetic_only_and_lists_rules_without_login(client):
    response = client.get("/documents/notice")

    assert response.status_code == 200
    body = response.json()
    assert "synthetic" in body["notice"].lower()
    assert set(body["allowed_types"]) == {"image/jpeg", "image/png", "application/pdf"}
    assert body["max_size_mb"] == 5


# --- Happy path (AC1) -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("content", "mime", "ext"),
    [(JPEG, "image/jpeg", ".jpg"), (PNG, "image/png", ".png"), (PDF, "application/pdf", ".pdf")],
)
def test_lf005_upload_is_stored_and_listed_with_type_and_time(
    client, make_user, storage_dir, content, mime, ext
):
    _, headers, app_id = new_application(client, make_user)

    response = upload(client, headers, app_id, content, doc_type="payslips")

    assert response.status_code == 201
    body = response.json()
    assert body["doc_type"] == "payslips"
    assert body["mime_type"] == mime
    assert body["size_bytes"] == len(content)
    assert body["uploaded_at"]
    files = stored_files(storage_dir)
    assert len(files) == 1 and files[0].suffix == ext and files[0].read_bytes() == content
    listing = client.get(f"/applications/{app_id}/documents", headers=headers)
    assert listing.status_code == 200
    assert [d["id"] for d in listing.json()] == [body["id"]]
    assert listing.json()[0]["doc_type"] == "payslips"


def test_lf005_upload_is_audited_without_filename(client, db, make_user):
    owner, headers, app_id = new_application(client, make_user)

    upload(client, headers, app_id, filename="CCCD_Nguyen_Van_An.jpg")

    entry = db.scalar(select(AuditLog).where(AuditLog.action == "document.upload"))
    assert entry.actor_id == owner.id and entry.target_type == "document"
    assert "CCCD" not in repr(vars(entry))


# --- Size (AC2) -------------------------------------------------------------------------


def test_lf005_file_of_exactly_5mb_is_accepted(client, make_user):
    _, headers, app_id = new_application(client, make_user)

    response = upload(client, headers, app_id, JPEG + b"\x00" * (5 * MB - len(JPEG)))

    assert response.status_code == 201


def test_lf005_file_over_5mb_rejected_with_actionable_message_and_nothing_stored(
    client, db, make_user, storage_dir
):
    _, headers, app_id = new_application(client, make_user)

    response = upload(client, headers, app_id, JPEG + b"\x00" * (5 * MB - len(JPEG) + 1))

    assert response.status_code == 413
    detail = response.json()["detail"]
    assert "5 MB" in detail and "smaller" in detail
    assert doc_count(db) == 0 and stored_files(storage_dir) == []


def test_lf005_oversized_request_is_refused_before_parsing(client, db, make_user, storage_dir):
    _, headers, app_id = new_application(client, make_user)

    response = upload(client, headers, app_id, JPEG + b"\x00" * (8 * MB))

    assert response.status_code == 413
    # The middleware's own message: proves the guard ran, not just the per-file check.
    assert "request is too large" in response.json()["detail"]
    assert doc_count(db) == 0 and stored_files(storage_dir) == []


def test_lf005_empty_file_rejected(client, db, make_user):
    _, headers, app_id = new_application(client, make_user)

    response = upload(client, headers, app_id, b"")

    assert response.status_code == 422
    assert "empty" in response.json()["detail"].lower()
    assert doc_count(db) == 0


# --- Type (AC2) ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("content", "filename", "content_type"),
    [
        (b"MZ\x90\x00" + b"\x00" * 50, "setup.exe", "application/octet-stream"),
        (b"just some text", "notes.txt", "text/plain"),
        (b"<html><script>alert(1)</script></html>", "page.html", "text/html"),
        (b"GIF89a" + b"\x00" * 50, "anim.gif", "image/gif"),
        (b"just some text", "fake.jpg", "image/jpeg"),  # renamed, still not an image
        (b"MZ\x90\x00" + b"\x00" * 50, "fake.pdf", "application/pdf"),
    ],
)
def test_lf005_unsupported_type_rejected_naming_the_fix(
    client, db, make_user, storage_dir, content, filename, content_type
):
    _, headers, app_id = new_application(client, make_user)

    response = upload(
        client, headers, app_id, content, filename=filename, content_type=content_type
    )

    assert response.status_code == 415
    assert "Upload a JPG, PNG or PDF" in response.json()["detail"]
    assert doc_count(db) == 0 and stored_files(storage_dir) == []


def test_lf005_detected_type_wins_over_declared_header_and_extension(client, make_user):
    _, headers, app_id = new_application(client, make_user)

    response = upload(
        client, headers, app_id, PNG, filename="x.pdf", content_type="application/pdf"
    )

    assert response.status_code == 201
    assert response.json()["mime_type"] == "image/png"


def test_lf005_unknown_document_type_rejected(client, db, make_user):
    _, headers, app_id = new_application(client, make_user)

    response = upload(client, headers, app_id, doc_type="selfie_with_pet")

    assert response.status_code == 422
    assert "doc_type" in response.text
    assert doc_count(db) == 0


# --- Retry without duplicates (AC4) ---------------------------------------------------------


def test_lf005_retrying_same_file_creates_no_duplicate(client, db, make_user, storage_dir):
    _, headers, app_id = new_application(client, make_user)

    first = upload(client, headers, app_id, JPEG)
    retry = upload(client, headers, app_id, JPEG)

    assert first.status_code == 201 and retry.status_code == 200
    assert retry.json()["id"] == first.json()["id"]
    assert doc_count(db) == 1 and len(stored_files(storage_dir)) == 1
    assert audit_actions(db).count("document.upload") == 1


@pytest.mark.parametrize("change", ["other_file", "other_type"])
def test_lf005_different_file_or_type_is_a_new_document(client, db, make_user, change):
    _, headers, app_id = new_application(client, make_user)
    upload(client, headers, app_id, JPEG)

    response = (
        upload(client, headers, app_id, PNG)
        if change == "other_file"
        else upload(client, headers, app_id, JPEG, doc_type="payslips")
    )

    assert response.status_code == 201
    assert doc_count(db) == 2


def test_lf005_database_enforces_uniqueness_of_content_per_application_and_type(
    client, db, make_user
):
    from sqlalchemy.exc import IntegrityError

    _, headers, app_id = new_application(client, make_user)
    first = upload(client, headers, app_id, JPEG).json()
    original = db.get(Document, first["id"])

    clone = Document(
        application_id=original.application_id,
        doc_type=original.doc_type,
        storage_key="another-key.jpg",
        mime_type=original.mime_type,
        size_bytes=original.size_bytes,
        sha256=original.sha256,
        uploaded_by=original.uploaded_by,
        uploaded_at=original.uploaded_at,
    )
    db.add(clone)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


# --- Access control (C-12, permission matrix) --------------------------------------------------


def test_lf005_borrower_cannot_upload_to_or_list_another_borrowers_application(
    client, db, make_user
):
    _, _, app_id = new_application(client, make_user)
    intruder, headers = make_user(Role.BORROWER)

    assert upload(client, headers, app_id).status_code == 403
    assert client.get(f"/applications/{app_id}/documents", headers=headers).status_code == 403
    assert doc_count(db) == 0
    denied = db.scalars(
        select(AuditLog).where(AuditLog.action == "application.access_denied")
    ).all()
    assert len(denied) == 2 and all(d.actor_id == intruder.id for d in denied)


def test_lf005_officer_can_upload_list_and_download_and_reads_are_audited(client, db, make_user):
    _, _, app_id = new_application(client, make_user)
    officer, headers = make_user(Role.OFFICER)

    created = upload(client, headers, app_id, PDF, filename="a.pdf", content_type="application/pdf")
    listing = client.get(f"/applications/{app_id}/documents", headers=headers)
    download = client.get(
        f"/applications/{app_id}/documents/{created.json()['id']}/file", headers=headers
    )

    assert created.status_code == 201 and listing.status_code == 200
    assert download.status_code == 200 and download.content == PDF
    actions = db.scalars(select(AuditLog.action).where(AuditLog.actor_id == officer.id)).all()
    assert {"document.upload", "document.list", "document.download"} <= set(actions)


def test_lf005_supervisor_cannot_upload_but_can_list_and_download(client, db, make_user):
    _, owner_headers, app_id = new_application(client, make_user)
    created = upload(client, owner_headers, app_id).json()
    supervisor, headers = make_user(Role.SUPERVISOR)

    refused = upload(client, headers, app_id, PNG)
    listing = client.get(f"/applications/{app_id}/documents", headers=headers)
    download = client.get(f"/applications/{app_id}/documents/{created['id']}/file", headers=headers)

    assert refused.status_code == 403
    assert listing.status_code == 200 and download.status_code == 200
    actions = db.scalars(select(AuditLog.action).where(AuditLog.actor_id == supervisor.id)).all()
    assert "access.denied" in actions and "document.download" in actions
    assert doc_count(db) == 1


def test_lf005_borrower_reading_own_documents_is_not_audited(client, db, make_user):
    _, headers, app_id = new_application(client, make_user)
    created = upload(client, headers, app_id).json()

    client.get(f"/applications/{app_id}/documents", headers=headers)
    client.get(f"/applications/{app_id}/documents/{created['id']}/file", headers=headers)

    assert "document.list" not in audit_actions(db)
    assert "document.download" not in audit_actions(db)


def test_lf005_unauthenticated_requests_401(client, make_user):
    _, headers, app_id = new_application(client, make_user)
    created = upload(client, headers, app_id).json()

    assert client.get(f"/applications/{app_id}/documents").status_code == 401
    assert client.get(f"/applications/{app_id}/documents/{created['id']}/file").status_code == 401
    assert (
        client.post(
            f"/applications/{app_id}/documents",
            data={"doc_type": "national_id"},
            files={"file": ("a.jpg", JPEG, "image/jpeg")},
        ).status_code
        == 401
    )


def test_lf005_document_id_from_another_application_is_404(client, make_user):
    _, headers_a, app_a = new_application(client, make_user)
    _, headers_b, app_b = new_application(client, make_user)
    doc_a = upload(client, headers_a, app_a).json()

    response = client.get(f"/applications/{app_b}/documents/{doc_a['id']}/file", headers=headers_b)

    assert response.status_code == 404


def test_lf005_missing_application_404(client, make_user):
    _, headers = make_user(Role.BORROWER)

    response = upload(client, headers, "00000000-0000-4000-8000-000000000000")

    assert response.status_code == 404


# --- Status and limits ----------------------------------------------------------------------------


def test_lf005_upload_refused_when_application_no_longer_accepts_documents(
    client, db, make_user, storage_dir
):
    _, headers, app_id = new_application(client, make_user)
    db.scalar(select(Application)).status = "APPROVED"
    db.commit()

    response = upload(client, headers, app_id)

    assert response.status_code == 409
    assert doc_count(db) == 0 and stored_files(storage_dir) == []


def test_lf005_document_count_per_application_is_capped(client, make_user, monkeypatch):
    monkeypatch.setattr(get_settings(), "max_documents_per_application", 2)
    _, headers, app_id = new_application(client, make_user)
    assert upload(client, headers, app_id, JPEG).status_code == 201
    assert upload(client, headers, app_id, PNG).status_code == 201

    over = upload(client, headers, app_id, PDF)
    retry_existing = upload(client, headers, app_id, PNG)

    assert over.status_code == 409 and "2" in over.json()["detail"]
    assert retry_existing.status_code == 200  # a retry of an existing file is never "too many"


# --- Storage safety ---------------------------------------------------------------------


def test_lf005_hostile_filename_cannot_escape_storage_and_is_never_stored(
    client, db, make_user, storage_dir
):
    _, headers, app_id = new_application(client, make_user)

    response = upload(client, headers, app_id, filename="../../etc/passwd.jpg")

    assert response.status_code == 201
    (stored,) = stored_files(storage_dir)
    assert storage_dir.resolve() in stored.resolve().parents
    assert "passwd" not in stored.name
    assert "passwd" not in response.text
    assert "passwd" not in repr(vars(db.scalar(select(Document))))


def test_lf005_file_is_removed_if_recording_the_upload_fails(
    client, db, make_user, storage_dir, monkeypatch
):
    _, headers, app_id = new_application(client, make_user)

    def boom(*args, **kwargs):
        raise RuntimeError("audit store unavailable")

    monkeypatch.setattr("app.services.document_service.audit_service.record", boom)

    with pytest.raises(RuntimeError):
        upload(client, headers, app_id)

    assert stored_files(storage_dir) == []
    assert doc_count(db) == 0


def test_lf005_stored_files_live_outside_the_application_package():
    storage = Path(get_settings().storage_dir).resolve()
    app_package = Path(__file__).resolve().parents[1] / "app"

    assert app_package not in storage.parents and storage != app_package


def test_lf005_file_is_content_hashed_for_dedup(client, db, make_user):
    _, headers, app_id = new_application(client, make_user)

    upload(client, headers, app_id, PNG)

    assert db.scalar(select(Document.sha256)) == hashlib.sha256(PNG).hexdigest()


# --- Download ---------------------------------------------------------------------------


def test_lf005_download_returns_exact_bytes_as_attachment_that_browsers_cannot_sniff(
    client, make_user
):
    _, headers, app_id = new_application(client, make_user)
    created = upload(client, headers, app_id, PNG, filename="evil.html").json()

    response = client.get(f"/applications/{app_id}/documents/{created['id']}/file", headers=headers)

    assert response.status_code == 200 and response.content == PNG
    assert response.headers["content-type"] == "image/png"
    assert response.headers["content-disposition"].startswith("attachment")
    assert "evil" not in response.headers["content-disposition"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "no-store" in response.headers["cache-control"]
