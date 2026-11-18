"""LF-010 Officer queue (docs/04; BR-10, BR-11). Flags high_dti / fast_track are set directly
here: LF-008 and LF-009 will compute them later."""

import time
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.application import Application, ApplicationStatus
from app.models.audit_log import AuditLog
from app.models.borrower_profile import BorrowerProfile
from app.models.status_history import StatusHistory
from app.models.user import Role

from .test_lf004_submit import submit
from .test_lf005_upload import JPEG, upload

MANDATORY_SALARIED = [
    ("national_id", "scan.jpg"),
    ("labour_contract", "contract.jpg"),
    ("payslips", "pay.jpg"),
]


def new_application(client, make_user, income_type="salaried", name="Nguyen Van An"):
    owner, headers = make_user(Role.BORROWER)
    response = submit(client, headers, profile={"income_type": income_type, "full_name": name})
    assert response.status_code == 201
    return owner, headers, response.json()["id"]


def upload_all(client, headers, app_id):
    for index, (doc_type, filename) in enumerate(MANDATORY_SALARIED):
        content = JPEG + bytes([index])  # distinct content so no upload is a duplicate
        assert upload(client, headers, app_id, content, doc_type=doc_type, filename=filename)


def status_of(db, app_id):
    db.expire_all()
    return db.get(Application, uuid.UUID(app_id)).status


def queued(client, make_user, db, **flags):
    """A fully documented application, now IN_REVIEW, with flags set directly."""
    _, headers, app_id = new_application(client, make_user)
    upload_all(client, headers, app_id)
    application = db.get(Application, uuid.UUID(app_id))
    for key, value in flags.items():
        setattr(application, key, value)
    db.commit()
    return app_id


def get_queue(client, headers, **params):
    return client.get("/queue", headers=headers, params=params)


# --- moving a file into the queue ----------------------------------------------------------


def test_lf010_file_is_queued_once_every_mandatory_document_is_in(client, db, make_user):
    _, headers, app_id = new_application(client, make_user)

    upload(client, headers, app_id, JPEG, doc_type="national_id")
    assert status_of(db, app_id) == "SUBMITTED"  # still missing documents

    upload(client, headers, app_id, JPEG + b"1", doc_type="labour_contract")
    upload(client, headers, app_id, JPEG + b"2", doc_type="payslips")
    assert status_of(db, app_id) == "IN_REVIEW"
    history = db.scalars(
        select(StatusHistory).where(StatusHistory.application_id == uuid.UUID(app_id))
    ).all()
    assert [(h.from_status, h.to_status) for h in history] == [
        ("DRAFT", "SUBMITTED"),
        ("SUBMITTED", "IN_REVIEW"),
    ]
    assert "application.queued" in db.scalars(select(AuditLog.action)).all()


def test_lf010_officer_waiving_the_last_missing_document_queues_the_file(client, db, make_user):
    _, _, app_id = new_application(client, make_user, income_type="freelance")
    _, officer = make_user(Role.OFFICER)
    body = client.get(f"/applications/{app_id}/checklist", headers=officer).json()
    mandatory = [r for r in body["requirements"] if r["mandatory"]]

    for requirement in mandatory:
        assert status_of(db, app_id) == "SUBMITTED"
        response = client.post(
            f"/applications/{app_id}/exceptions",
            headers=officer,
            json={"requirement_id": requirement["id"]},
        )
        assert response.status_code == 201

    assert status_of(db, app_id) == "IN_REVIEW"


def test_lf010_borrower_can_still_add_an_optional_document_once_queued(client, db, make_user):
    _, headers, app_id = new_application(client, make_user)
    upload_all(client, headers, app_id)

    response = upload(client, headers, app_id, JPEG + b"9", doc_type="tax_return")

    assert response.status_code == 201
    assert status_of(db, app_id) == "IN_REVIEW"


# --- AC1: listing, oldest first -------------------------------------------------------------


def test_lf010_queue_lists_in_review_files_oldest_first_with_applicant_amount_flags_age(
    client, db, clock, make_user
):
    first = queued(client, make_user, db, exception_flag=True)
    clock.advance(hours=3)
    second = queued(client, make_user, db, high_dti=True, fast_track=True)
    clock.advance(hours=1)
    _, officer = make_user(Role.OFFICER)  # logs in now: access tokens are short-lived

    response = get_queue(client, officer)

    assert response.status_code == 200
    body = response.json()
    assert [i["id"] for i in body["items"]] == [first, second]
    assert body["total"] == 2 and body["message"] is None
    older, newer = body["items"]
    assert older["applicant_name"] == "Nguyen Van An"
    assert older["amount_vnd"] == 100_000_000 and older["term_months"] == 24
    assert older["flags"] == ["exception"]
    assert newer["flags"] == ["high_dti", "fast_track"]
    assert older["age_hours"] == pytest.approx(4.0, abs=0.01)
    assert newer["age_hours"] == pytest.approx(1.0, abs=0.01)


def test_lf010_newest_first_when_asked(client, db, clock, make_user):
    first = queued(client, make_user, db)
    clock.advance(hours=1)
    second = queued(client, make_user, db)
    _, officer = make_user(Role.OFFICER)

    body = get_queue(client, officer, sort="newest").json()

    assert [i["id"] for i in body["items"]] == [second, first]


def test_lf010_files_not_yet_in_review_are_not_listed_by_default(client, db, make_user):
    _, officer = make_user(Role.OFFICER)
    _, _, waiting = new_application(client, make_user)  # SUBMITTED, documents missing
    ready = queued(client, make_user, db)

    default = get_queue(client, officer).json()
    submitted = get_queue(client, officer, status="SUBMITTED").json()

    assert [i["id"] for i in default["items"]] == [ready]
    assert [i["id"] for i in submitted["items"]] == [waiting]


# --- AC2: filters ---------------------------------------------------------------------------


@pytest.mark.parametrize("flag", ["exception", "high_dti", "fast_track"])
def test_lf010_flag_filter_returns_only_matching_rows(client, db, make_user, flag):
    _, officer = make_user(Role.OFFICER)
    column = "exception_flag" if flag == "exception" else flag
    match = queued(client, make_user, db, **{column: True})
    queued(client, make_user, db)  # no flags

    body = get_queue(client, officer, flag=flag).json()

    assert [i["id"] for i in body["items"]] == [match]
    assert body["total"] == 1


def test_lf010_unknown_flag_or_status_is_rejected_with_the_allowed_values(client, make_user):
    _, officer = make_user(Role.OFFICER)

    bad_flag = get_queue(client, officer, flag="urgent")
    bad_status = get_queue(client, officer, status="DRAFT")

    assert bad_flag.status_code == 422 and bad_status.status_code == 422
    assert "exception" in str(bad_flag.json()) and "high_dti" in str(bad_flag.json())
    assert "IN_REVIEW" in str(bad_status.json())


# --- AC3: empty queue -----------------------------------------------------------------------


def test_lf010_empty_queue_says_no_applications_waiting(client, make_user):
    _, officer = make_user(Role.OFFICER)

    body = get_queue(client, officer).json()

    assert body["items"] == [] and body["total"] == 0
    assert body["message"] == "No applications waiting"


# --- access control -------------------------------------------------------------------------


def test_lf010_borrower_and_anonymous_cannot_open_the_queue(client, db, make_user):
    _, borrower = make_user(Role.BORROWER)

    assert get_queue(client, borrower).status_code == 403
    assert client.get("/queue").status_code == 401
    denied = db.scalars(select(AuditLog).where(AuditLog.action == "access.denied")).all()
    assert len(denied) == 1


def test_lf010_officer_sees_unassigned_and_own_files_but_not_a_colleagues(client, db, make_user):
    officer_user, officer = make_user(Role.OFFICER)
    other_user, _ = make_user(Role.OFFICER)
    _, supervisor = make_user(Role.SUPERVISOR)
    unassigned = queued(client, make_user, db)
    mine = queued(client, make_user, db)
    theirs = queued(client, make_user, db)
    db.get(Application, uuid.UUID(mine)).assigned_officer = officer_user.id
    db.get(Application, uuid.UUID(theirs)).assigned_officer = other_user.id
    db.commit()

    officer_ids = {i["id"] for i in get_queue(client, officer).json()["items"]}
    supervisor_ids = {i["id"] for i in get_queue(client, supervisor).json()["items"]}

    assert officer_ids == {unassigned, mine}
    assert supervisor_ids == {unassigned, mine, theirs}


def test_lf010_each_queue_read_is_audited_without_applicant_data(client, db, make_user):
    officer_user, officer = make_user(Role.OFFICER)
    queued(client, make_user, db)

    get_queue(client, officer)

    entries = db.scalars(select(AuditLog).where(AuditLog.action == "queue.view")).all()
    assert [e.actor_id for e in entries] == [officer_user.id]
    assert entries[0].application_id is None


# --- AC4: paging and speed ------------------------------------------------------------------


def test_lf010_first_page_of_1000_applications_loads_within_two_seconds(
    client, db, clock, make_user
):
    _, officer = make_user(Role.OFFICER)
    owner, _ = make_user(Role.BORROWER)
    profile = BorrowerProfile(user_id=owner.id, full_name="Synthetic Person")
    db.add(profile)
    db.flush()
    start = clock()
    db.add_all(
        Application(
            borrower_profile_id=profile.id,
            created_by=owner.id,
            amount_vnd=Decimal(50_000_000),
            term_months=12,
            status=ApplicationStatus.IN_REVIEW.value,
            submitted_at=start - timedelta(minutes=n),
        )
        for n in range(1000)
    )
    db.commit()

    began = time.perf_counter()
    response = get_queue(client, officer, limit=50)
    elapsed = time.perf_counter() - began

    body = response.json()
    assert response.status_code == 200 and body["total"] == 1000 and len(body["items"]) == 50
    assert elapsed < 2.0
    second_page = get_queue(client, officer, limit=50, offset=50).json()["items"]
    assert not {i["id"] for i in body["items"]} & {i["id"] for i in second_page}
