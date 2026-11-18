"""LF-013 CSV bulk import (docs/04; BR-21, D-030)."""

import csv
import io
import uuid
from datetime import date

import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.borrower_profile import BorrowerProfile
from app.models.consent import Consent
from app.models.user import Role
from app.services.import_service import COLUMNS, TEMPLATE_CSV

from .test_lf010_queue import new_application

URL = "/imports/applications"


def good_row(email="ana@example.com", **overrides):
    row = {
        "email": email,
        "full_name": "Nguyen Van An",
        "date_of_birth": "1990-05-01",
        "national_id": "012345678901",
        "address": "1 Example Street, Hanoi",
        "income_type": "salaried",
        "monthly_income_vnd": "30000000",
        "existing_debt_payment_vnd": "0",
        "amount_vnd": "50000000",
        "term_months": "12",
        "purpose": "",
    }
    return {**row, **overrides}


def make_csv(rows, columns=COLUMNS, bom=False) -> bytes:
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=list(columns), extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return (("﻿" if bom else "") + out.getvalue()).encode("utf-8")


def post(client, headers, content, name="people.csv"):
    return client.post(URL, headers=headers, files={"file": (name, content, "text/csv")})


@pytest.fixture
def officer(make_user):
    return make_user(Role.OFFICER)


def drafts(db):
    db.expire_all()
    return db.scalars(select(Application).where(Application.import_job_id.is_not(None))).all()


# --- AC1: a valid file -> DRAFT applications and a summary -----------------------------------


def test_lf013_valid_file_creates_draft_applications_and_a_summary(client, db, officer):
    rows = [good_row("a@example.com"), good_row("b@example.com", amount_vnd="80000000")]

    response = post(client, officer[1], make_csv(rows))

    assert response.status_code == 201
    body = response.json()
    assert (body["total_rows"], body["imported"], body["duplicates"], body["invalid"]) == (
        2,
        2,
        0,
        0,
    )
    assert body["issues"] == []
    assert [c["row"] for c in body["created"]] == [2, 3]
    stored = drafts(db)
    assert {a.status for a in stored} == {"DRAFT"}
    assert {int(a.amount_vnd) for a in stored} == {50_000_000, 80_000_000}
    assert all(a.created_by == officer[0].id and a.submitted_at is None for a in stored)
    assert all(a.annual_rate is not None and a.income_type == "salaried" for a in stored)


def test_lf013_imported_profiles_have_no_account_and_no_consent_is_recorded(client, db, officer):
    before = db.scalar(select(func.count()).select_from(Consent))

    post(client, officer[1], make_csv([good_row("ana@example.com")]))

    profile = db.scalars(
        select(BorrowerProfile).where(BorrowerProfile.contact_email == "ana@example.com")
    ).one()
    assert profile.user_id is None
    assert profile.full_name == "Nguyen Van An"
    assert db.scalar(select(func.count()).select_from(Consent)) == before  # BR-21: none invented
    assert "consent.give" not in db.scalars(select(AuditLog.action)).all()


def test_lf013_imported_drafts_are_inert_nothing_queues_or_checks_them(client, db, officer):
    created = post(client, officer[1], make_csv([good_row()])).json()["created"][0]

    for status in ("IN_REVIEW", "SUBMITTED", "REFERRED"):
        listed = client.get("/queue", headers=officer[1], params={"status": status}).json()
        assert listed["items"] == []
    cic = client.post(f"/applications/{created['application_id']}/cic-check", headers=officer[1])
    assert cic.status_code == 409
    assert drafts(db)[0].status == "DRAFT"  # BR-15: nothing moved it


def test_lf013_import_is_audited_per_application_and_per_job(client, db, officer):
    body = post(
        client, officer[1], make_csv([good_row("a@example.com"), good_row("b@example.com")])
    ).json()

    actions = db.scalars(
        select(AuditLog.action).where(AuditLog.actor_id == officer[0].id).order_by(AuditLog.seq)
    ).all()
    assert actions.count("application.imported") == 2
    assert actions.count("import.completed") == 1
    job_audit = db.scalars(select(AuditLog).where(AuditLog.action == "import.completed")).one()
    assert str(job_audit.target_id) == body["job_id"]


def test_lf013_utf8_bom_and_vietnamese_names_are_accepted(client, db, officer):
    rows = [good_row(full_name="Nguyễn Thị Hồng", address="12 Phố Huế, Hà Nội")]

    response = post(client, officer[1], make_csv(rows, bom=True))

    assert response.status_code == 201 and response.json()["imported"] == 1
    profile = db.scalars(select(BorrowerProfile).where(BorrowerProfile.user_id.is_(None))).one()
    assert profile.full_name == "Nguyễn Thị Hồng"


def test_lf013_blank_optional_columns_use_defaults(client, db, officer):
    rows = [good_row(existing_debt_payment_vnd="", purpose="")]

    assert post(client, officer[1], make_csv(rows)).json()["imported"] == 1
    profile = db.scalars(select(BorrowerProfile).where(BorrowerProfile.user_id.is_(None))).one()
    assert int(profile.existing_debt_payment_vnd) == 0


# --- AC2: bad rows are reported, good rows still imported ------------------------------------

THIS_YEAR = date.today().year


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"national_id": "123"}, "national_id: National ID must be 12 digits"),
        ({"date_of_birth": "01/05/1990"}, "date_of_birth"),
        ({"date_of_birth": f"{THIS_YEAR - 10}-01-01"}, "at least 18"),
        ({"income_type": "pirate"}, "income_type"),
        ({"term_months": "7"}, "term_months: Term must be one of"),
        ({"amount_vnd": "5"}, "amount_vnd: Amount must be between"),
        ({"amount_vnd": "abc"}, "amount_vnd"),
        ({"amount_vnd": "120000000", "purpose": ""}, "purpose is required"),
        ({"full_name": ""}, "full_name"),
        ({"email": "not-an-email"}, "email: not a valid email address"),
        ({"monthly_income_vnd": "30,000,000"}, "monthly_income_vnd"),
    ],
)
def test_lf013_invalid_row_is_reported_with_its_row_number_and_reason(
    client, db, officer, overrides, expected
):
    rows = [good_row("ok@example.com"), {**good_row("bad@example.com"), **overrides}]

    body = post(client, officer[1], make_csv(rows)).json()

    assert (body["imported"], body["invalid"]) == (1, 1)
    issue = body["issues"][0]
    assert issue["row"] == 3 and issue["kind"] == "invalid"
    assert expected in issue["message"]
    assert [a.status for a in drafts(db)] == ["DRAFT"]  # the good row was still imported


def test_lf013_reports_never_repeat_the_submitted_values(client, officer):
    row = good_row(
        "bad@example.com", national_id="999000111", full_name="Secret Person", income_type="pirate"
    )

    text = post(client, officer[1], make_csv([row])).text

    for value in ("999000111", "Secret Person", "pirate", "bad@example.com"):
        assert value not in text


def test_lf013_row_with_more_values_than_columns_is_reported(client, officer):
    content = (
        make_csv([good_row()])
        + b"x@example.com,Name,1990-05-01,012345678901,Addr,salaried,1,0,50000000,12,,extra\n"
    )

    body = post(client, officer[1], content).json()

    assert body["imported"] == 1
    assert body["issues"][0]["message"] == "Row has more values than columns"


# --- AC3: whole-file refusals -----------------------------------------------------------------


def test_lf013_wrong_or_missing_columns_are_refused_naming_them(client, db, officer):
    columns = [c for c in COLUMNS if c != "term_months"] + ["shoe_size"]

    response = post(client, officer[1], make_csv([good_row()], columns=columns))

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "Missing columns: term_months" in detail and "Unexpected columns: shoe_size" in detail
    assert drafts(db) == []


def test_lf013_file_over_two_megabytes_is_refused(client, db, officer):
    big = make_csv([good_row()]) + b"x" * (get_settings().import_max_bytes + 1)

    response = post(client, officer[1], big)

    assert response.status_code == 422
    assert "2 MB or smaller" in response.json()["detail"]
    assert drafts(db) == []


def test_lf013_file_exactly_at_the_limit_is_not_refused_for_size(client, officer, monkeypatch):
    content = make_csv([good_row()])
    monkeypatch.setattr(get_settings(), "import_max_bytes", len(content))

    assert post(client, officer[1], content).status_code == 201


@pytest.mark.parametrize(
    ("name", "content", "status", "fragment"),
    [
        ("people.xlsx", b"a,b\n1,2\n", 415, "Upload a .csv file"),
        ("people.csv", b"\xff\xfe\x00bad", 422, "UTF-8"),
        ("people.csv", b"", 422, "no data rows"),
        ("people.csv", ",".join(COLUMNS).encode() + b"\n", 422, "no data rows"),
    ],
)
def test_lf013_unusable_files_are_refused_with_a_specific_message(
    client, officer, name, content, status, fragment
):
    response = post(client, officer[1], content, name=name)

    assert response.status_code == status
    assert fragment in response.json()["detail"]


def test_lf013_too_many_rows_are_refused(client, db, officer, monkeypatch):
    monkeypatch.setattr(get_settings(), "import_max_rows", 2)
    rows = [good_row(f"p{i}@example.com") for i in range(3)]

    response = post(client, officer[1], make_csv(rows))

    assert response.status_code == 422 and "at most 2" in response.json()["detail"]
    assert drafts(db) == []


# --- AC4: duplicates are detected and skipped -------------------------------------------------


def test_lf013_importing_the_same_file_twice_skips_every_row_the_second_time(client, db, officer):
    content = make_csv([good_row("a@example.com"), good_row("b@example.com")])

    first = post(client, officer[1], content).json()
    second = post(client, officer[1], content).json()

    assert first["imported"] == 2
    assert (second["imported"], second["duplicates"]) == (0, 2)
    assert {i["kind"] for i in second["issues"]} == {"duplicate"}
    assert len(drafts(db)) == 2


def test_lf013_duplicate_inside_one_file_keeps_the_first_row(client, db, officer):
    rows = [good_row("a@example.com"), good_row("A@Example.com", amount_vnd="90000000")]

    body = post(client, officer[1], make_csv(rows)).json()

    assert (body["imported"], body["duplicates"]) == (1, 1)
    assert body["issues"][0]["row"] == 3
    assert "Duplicate of row 2" in body["issues"][0]["message"]
    assert [int(a.amount_vnd) for a in drafts(db)] == [50_000_000]


def test_lf013_an_existing_borrower_is_skipped_and_never_changed(client, db, make_user, officer):
    owner, _, _ = new_application(client, make_user, name="Real Borrower")

    body = post(
        client, officer[1], make_csv([good_row(owner.email, full_name="Overwritten")])
    ).json()

    assert (body["imported"], body["duplicates"]) == (0, 1)
    db.expire_all()
    profile = db.scalars(select(BorrowerProfile).where(BorrowerProfile.user_id == owner.id)).one()
    assert profile.full_name == "Real Borrower"


# --- access control ---------------------------------------------------------------------------


def test_lf013_borrower_is_forbidden_and_the_refusal_is_audited(client, db, make_user):
    borrower, headers = make_user(Role.BORROWER)

    assert post(client, headers, make_csv([good_row()])).status_code == 403
    assert client.get(URL + "/template", headers=headers).status_code == 403
    denied = db.scalars(
        select(AuditLog).where(AuditLog.actor_id == borrower.id, AuditLog.action == "access.denied")
    ).all()
    assert len(denied) == 2
    assert drafts(db) == []


def test_lf013_requires_login(client):
    assert client.post(URL, files={"file": ("a.csv", b"x", "text/csv")}).status_code == 401
    assert client.get(URL + "/template").status_code == 401


def test_lf013_supervisor_can_import_too(client, make_user):
    supervisor = make_user(Role.SUPERVISOR)

    assert post(client, supervisor[1], make_csv([good_row()])).status_code == 201


def test_lf013_template_downloads_and_is_itself_a_valid_import(client, officer):
    response = client.get(URL + "/template", headers=officer[1])

    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    assert response.text == TEMPLATE_CSV
    assert post(client, officer[1], response.content).json()["imported"] == 1


def test_lf013_imported_draft_can_be_opened_by_staff_with_a_masked_id(client, officer):
    created = post(client, officer[1], make_csv([good_row()])).json()["created"][0]

    detail = client.get(
        f"/applications/{created['application_id']}/review", headers=officer[1]
    ).json()

    assert detail["status"] == "DRAFT"
    assert detail["applicant"]["national_id_masked"] == "********8901"
    assert uuid.UUID(created["application_id"])
