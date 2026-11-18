"""LF-013 CSV bulk import of applications (docs/04, D-030).

Every valid row becomes a DRAFT application owned by a profile with no account yet. Nothing
processes a DRAFT: it is not queued, checked or shown to anyone as a borrower's own, because
the borrower has not given consent (BR-21). Rows are validated with the same rules as a
submitted application. Error messages name the column and the rule, never the value.
"""

import csv
import hashlib
import io
from datetime import datetime
from decimal import Decimal

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.consent import CONSENT_VERSION
from app.core.errors import UnprocessableEntity, UnsupportedMediaType
from app.models.application import Application, ApplicationStatus
from app.models.borrower_profile import BorrowerProfile
from app.models.import_job import ImportJob
from app.models.status_history import StatusHistory
from app.models.user import User
from app.schemas.application import ApplicationSubmitIn
from app.schemas.import_ import ImportedRow, ImportResultOut, ImportRowIssue
from app.services import application_service, audit_service
from app.services.calculator_service import rate_for_term

COLUMNS = (
    "email",
    "full_name",
    "date_of_birth",
    "national_id",
    "address",
    "income_type",
    "monthly_income_vnd",
    "existing_debt_payment_vnd",
    "amount_vnd",
    "term_months",
    "purpose",
)
_OPTIONAL = frozenset({"existing_debt_payment_vnd", "purpose"})
_PROFILE_COLUMNS = frozenset(COLUMNS[1:8])
_EMAIL = TypeAdapter(EmailStr)

# Synthetic example only (BR-24): never a real person.
TEMPLATE_CSV = (
    ",".join(COLUMNS) + "\n"
    "applicant@example.com,Nguyen Van A,1990-05-01,012345678901,1 Example Street Hanoi,"
    "salaried,30000000,0,50000000,12,\n"
)


def _read_rows(data: bytes) -> list[dict[str, str | None]]:
    """Decode and parse the file, or refuse it as a whole with a specific message."""
    settings = get_settings()
    if len(data) > settings.import_max_bytes:
        limit_mb = settings.import_max_bytes // (1024 * 1024)
        raise UnprocessableEntity(
            f"The file is too large. CSV files must be {limit_mb} MB or smaller."
        )
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise UnprocessableEntity("The file is not UTF-8 text. Save it as CSV (UTF-8).") from None
    if not text.strip():
        raise UnprocessableEntity("The file has no data rows.")
    try:
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        header = reader.fieldnames or []
        missing = [c for c in COLUMNS if c not in header]
        unexpected = [c for c in header if c not in COLUMNS]
        if missing or unexpected:
            parts = []
            if missing:
                parts.append(f"Missing columns: {', '.join(missing)}.")
            if unexpected:
                parts.append(f"Unexpected columns: {', '.join(unexpected)}.")
            raise UnprocessableEntity(" ".join(parts) + " Use the template's column names.")
        rows = list(reader)
    except csv.Error:
        raise UnprocessableEntity("The file is not a valid CSV.") from None
    if not rows:
        raise UnprocessableEntity("The file has no data rows.")
    if len(rows) > settings.import_max_rows:
        raise UnprocessableEntity(
            f"The file has too many rows. Import at most {settings.import_max_rows} at a time."
        )
    return rows  # type: ignore[return-value]


def _validate(row: dict[str, str | None], *, today: object) -> tuple[str, ApplicationSubmitIn]:
    """Return (email, validated submission) or raise ValueError with a message for the report."""
    if None in row:  # DictReader's key for values beyond the header
        raise ValueError("Row has more values than columns")
    values = {k: (v or "").strip() for k, v in row.items() if k is not None}
    try:
        email = str(_EMAIL.validate_python(values["email"])).lower()
    except ValidationError:
        raise ValueError("email: not a valid email address") from None

    def number(column: str) -> object:
        return values[column] if values[column] != "" or column not in _OPTIONAL else 0

    try:
        submission = ApplicationSubmitIn.model_validate(
            {
                "amount_vnd": values["amount_vnd"],
                "term_months": values["term_months"],
                "purpose": values["purpose"] or None,
                "profile": {
                    **{c: values[c] for c in _PROFILE_COLUMNS if c != "existing_debt_payment_vnd"},
                    "existing_debt_payment_vnd": number("existing_debt_payment_vnd"),
                },
                "consent_accepted": True,  # only to reuse the purpose rule; no consent is recorded
                "consent_version": CONSENT_VERSION,
            }
        )
    except ValidationError as error:
        problems = []
        for item in error.errors():
            column = str(item["loc"][-1]) if item["loc"] else "purpose"
            problems.append(f"{column}: {str(item['msg']).removeprefix('Value error, ')}")
        raise ValueError("; ".join(problems)) from None
    try:
        application_service.check_age(
            submission.profile.date_of_birth,
            submission.term_months,
            today=today,  # type: ignore[arg-type]
        )
    except UnprocessableEntity as refusal:
        raise ValueError(f"date_of_birth: {refusal.detail}") from None
    return email, submission


def _known_emails(db: Session, emails: set[str]) -> set[str]:
    if not emails:
        return set()
    registered = db.scalars(select(User.email).where(User.email.in_(emails)))
    imported = db.scalars(
        select(BorrowerProfile.contact_email).where(
            BorrowerProfile.contact_email.in_(emails), BorrowerProfile.user_id.is_(None)
        )
    )
    return {e for e in (*registered, *imported) if e}


def import_applications(
    db: Session, *, user: User, filename: str | None, data: bytes, now: datetime, ip: str | None
) -> ImportResultOut:
    if not (filename or "").lower().endswith(".csv"):
        raise UnsupportedMediaType("Upload a .csv file.")
    rows = _read_rows(data)

    issues: list[ImportRowIssue] = []
    valid: list[tuple[int, str, ApplicationSubmitIn]] = []
    for number, row in enumerate(rows, start=2):
        try:
            email, submission = _validate(row, today=now.date())
        except ValueError as problem:
            issues.append(ImportRowIssue(row=number, kind="invalid", message=str(problem)))
            continue
        valid.append((number, email, submission))

    known = _known_emails(db, {email for _, email, _ in valid})
    first_seen: dict[str, int] = {}
    to_create: list[tuple[int, str, ApplicationSubmitIn]] = []
    for number, email, submission in valid:
        if email in first_seen:
            message = f"Duplicate of row {first_seen[email]} in this file; skipped"
            issues.append(ImportRowIssue(row=number, kind="duplicate", message=message))
        elif email in known:
            message = "A borrower with this email already exists or was already imported; skipped"
            issues.append(ImportRowIssue(row=number, kind="duplicate", message=message))
        else:
            first_seen[email] = number
            to_create.append((number, email, submission))

    job = ImportJob(
        created_by=user.id,
        file_sha256=hashlib.sha256(data).hexdigest(),
        total_rows=len(rows),
        rows_imported=0,
        rows_duplicate=0,
        rows_invalid=0,
        created_at=now,
    )
    db.add(job)
    db.flush()

    created: list[ImportedRow] = []
    for number, email, submission in to_create:
        try:
            with db.begin_nested():  # a concurrent import of the same email skips just this row
                application = _create_draft(db, user, job, email, submission, now)
        except IntegrityError:
            issues.append(
                ImportRowIssue(
                    row=number,
                    kind="duplicate",
                    message="A borrower with this email was imported at the same time; skipped",
                )
            )
            continue
        created.append(ImportedRow(row=number, application_id=application.id))
        audit_service.record(
            db,
            action="application.imported",
            now=now,
            actor_id=user.id,
            target_type="application",
            target_id=application.id,
            application_id=application.id,
            ip_address=ip,
        )

    issues.sort(key=lambda i: i.row)
    job.rows_imported = len(created)
    job.rows_invalid = sum(1 for i in issues if i.kind == "invalid")
    job.rows_duplicate = sum(1 for i in issues if i.kind == "duplicate")
    audit_service.record(
        db,
        action="import.completed",
        now=now,
        actor_id=user.id,
        target_type="import_job",
        target_id=job.id,
        ip_address=ip,
    )
    db.commit()
    return ImportResultOut(
        job_id=job.id,
        total_rows=job.total_rows,
        imported=job.rows_imported,
        duplicates=job.rows_duplicate,
        invalid=job.rows_invalid,
        issues=issues,
        created=created,
    )


def _create_draft(
    db: Session,
    user: User,
    job: ImportJob,
    email: str,
    data: ApplicationSubmitIn,
    now: datetime,
) -> Application:
    profile = BorrowerProfile(
        user_id=None,
        contact_email=email,
        full_name=data.profile.full_name,
        date_of_birth=data.profile.date_of_birth,
        national_id=data.profile.national_id,
        address=data.profile.address,
        income_type=data.profile.income_type.value,
        monthly_income_vnd=Decimal(data.profile.monthly_income_vnd),
        existing_debt_payment_vnd=Decimal(data.profile.existing_debt_payment_vnd),
    )
    db.add(profile)
    db.flush()
    application = Application(
        borrower_profile_id=profile.id,
        created_by=user.id,
        amount_vnd=Decimal(data.amount_vnd),
        term_months=data.term_months,
        annual_rate=rate_for_term(data.term_months),
        income_type=data.profile.income_type.value,
        purpose=(data.purpose or "").strip() or None,
        status=ApplicationStatus.DRAFT.value,
        import_job_id=job.id,
    )
    db.add(application)
    db.flush()
    db.add(
        StatusHistory(
            application_id=application.id,
            from_status=None,
            to_status=ApplicationStatus.DRAFT.value,
            actor_id=user.id,
            changed_at=now,
        )
    )
    return application
