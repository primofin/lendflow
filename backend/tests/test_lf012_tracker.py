"""LF-012 Borrower status tracker (docs/04; docs/03 status mapping)."""

import uuid

import pytest
from sqlalchemy import select

from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.outbox import OutboxMessage
from app.models.status_history import StatusHistory
from app.models.user import Role

from .test_lf005_upload import JPEG, upload
from .test_lf010_queue import new_application, upload_all
from .test_lf011_decision import EXPLANATION, decide, reject_body

ASK = "Please upload a clearer copy of your latest bank statement."


@pytest.fixture
def officer(make_user):
    return make_user(Role.OFFICER)


@pytest.fixture
def supervisor(make_user):
    return make_user(Role.SUPERVISOR)


def queued_for(client, make_user):
    """A borrower's fully documented file, now IN_REVIEW. Returns (owner, headers, app_id)."""
    owner, headers, app_id = new_application(client, make_user)
    upload_all(client, headers, app_id)
    return owner, headers, app_id


def tracker(client, headers, app_id):
    return client.get(f"/applications/{app_id}/tracker", headers=headers)


def steps(body):
    return {s["label"]: s for s in body["steps"]}


def states(body):
    return [s["state"] for s in body["steps"]]


def set_status(db, app_id, status):
    application = db.get(Application, uuid.UUID(app_id))
    application.status = status
    db.commit()


def outbox(db, app_id=None):
    query = select(OutboxMessage).order_by(OutboxMessage.created_at)
    if app_id:
        query = query.where(OutboxMessage.application_id == uuid.UUID(app_id))
    return db.scalars(query).all()


# --- AC1/AC2: progress bar and timestamps ----------------------------------------------------


def test_lf012_submitted_file_shows_received_as_current_with_a_timestamp(client, make_user):
    _, headers, app_id = new_application(client, make_user)

    response = tracker(client, headers, app_id)

    assert response.status_code == 200
    body = response.json()
    assert [s["label"] for s in body["steps"]] == [
        "Received",
        "Under assessment",
        "Awaiting approval",
        "Completed",
    ]
    assert states(body) == ["current", "upcoming", "upcoming", "upcoming"]
    assert body["current_step"] == "Received"
    assert steps(body)["Received"]["updated_at"] is not None
    assert all(s["updated_at"] is None for s in body["steps"][1:])
    assert body["needs_info"] is None and body["decision"] is None


def test_lf012_each_step_shows_when_it_was_last_updated(client, db, clock, make_user):
    _, headers, app_id = new_application(client, make_user)
    clock.advance(minutes=5)
    upload_all(client, headers, app_id)  # queues the file five minutes after submission

    body = tracker(client, headers, app_id).json()

    assert states(body) == ["done", "current", "upcoming", "upcoming"]
    received, assessment = steps(body)["Received"], steps(body)["Under assessment"]
    assert received["updated_at"] < assessment["updated_at"]
    history = db.scalars(
        select(StatusHistory).where(StatusHistory.application_id == uuid.UUID(app_id))
    ).all()
    assert assessment["updated_at"].startswith(
        history[-1].changed_at.isoformat().replace("+00:00", "")[:19]
    )


def test_lf012_referred_file_shows_awaiting_approval_without_the_word_referred(
    client, clock, make_user, officer, supervisor
):
    _, headers, app_id = queued_for(client, make_user)
    clock.advance(minutes=1)
    decide(client, officer[1], app_id, {"outcome": "refer"})

    response = tracker(client, headers, app_id)

    body = response.json()
    assert body["current_step"] == "Awaiting approval"
    assert states(body) == ["done", "done", "current", "upcoming"]
    text = response.text.lower()
    assert "referred" not in text and str(supervisor[0].id) not in text
    assert str(officer[0].id) not in text


def test_lf012_direct_approval_skips_awaiting_approval(client, clock, make_user, officer):
    _, headers, app_id = queued_for(client, make_user)
    clock.advance(minutes=1)
    decide(client, officer[1], app_id, {"outcome": "approve"})

    body = tracker(client, headers, app_id).json()

    assert states(body) == ["done", "done", "skipped", "current"]
    assert steps(body)["Awaiting approval"]["updated_at"] is None
    assert steps(body)["Completed"]["updated_at"] is not None
    assert body["decision"]["outcome"] == "approve"


def test_lf012_rejection_shows_the_explanation_on_the_tracker(client, make_user, officer):
    _, headers, app_id = queued_for(client, make_user)
    decide(client, officer[1], app_id, reject_body())

    body = tracker(client, headers, app_id).json()

    assert body["current_step"] == "Completed"
    assert body["decision"]["explanation"] == EXPLANATION


# --- AC3: NEEDS_INFO lists the exact missing items -------------------------------------------


def test_lf012_needs_info_lists_exactly_the_missing_required_documents_and_an_upload_url(
    client, db, make_user
):
    _, headers, app_id = new_application(client, make_user)
    set_status(db, app_id, "NEEDS_INFO")
    upload(client, headers, app_id, JPEG, doc_type="national_id")

    body = tracker(client, headers, app_id).json()

    info = body["needs_info"]
    assert [m["label"] for m in info["missing_documents"]] == [
        "Labour contract or employer confirmation",
        "Payslips or bank statements (last 3 months)",
    ]
    assert info["missing_documents"][1]["accepted_types"] == ["bank_statements", "payslips"]
    assert info["upload_url"] == f"/applications/{app_id}/documents"
    assert info["can_resubmit"] is False
    assert body["current_step"] == "Under assessment"


def test_lf012_needs_info_shows_the_officers_request(client, make_user, officer):
    _, headers, app_id = queued_for(client, make_user)
    decide(client, officer[1], app_id, {"outcome": "request_info", "explanation": ASK})

    body = tracker(client, headers, app_id).json()

    assert body["needs_info"]["message"] == ASK
    assert body["needs_info"]["missing_documents"] == []
    assert body["needs_info"]["can_resubmit"] is True


# --- access ----------------------------------------------------------------------------------


def test_lf012_a_borrower_cannot_see_another_borrowers_tracker(client, db, make_user):
    _, _, app_id = new_application(client, make_user)
    _, stranger = make_user(Role.BORROWER)

    assert tracker(client, stranger, app_id).status_code == 403
    assert client.get(f"/applications/{app_id}/tracker").status_code == 401
    assert tracker(client, stranger, str(uuid.uuid4())).status_code == 404
    denied = db.scalars(
        select(AuditLog).where(AuditLog.action == "application.access_denied")
    ).all()
    assert len(denied) == 1


def test_lf012_staff_reads_of_the_tracker_are_audited(client, db, make_user, officer):
    _, _, app_id = new_application(client, make_user)

    assert tracker(client, officer[1], app_id).status_code == 200
    reads = db.scalars(select(AuditLog).where(AuditLog.action == "application.read")).all()
    assert [r.actor_id for r in reads] == [officer[0].id]


# --- resubmission ----------------------------------------------------------------------------


def test_lf012_borrower_answers_a_request_and_the_file_returns_to_the_same_officer(
    client, db, clock, make_user, officer
):
    _, headers, app_id = queued_for(client, make_user)
    clock.advance(minutes=1)
    decide(client, officer[1], app_id, {"outcome": "request_info", "explanation": ASK})
    clock.advance(minutes=1)
    extra = upload(client, headers, app_id, JPEG + b"x", doc_type="bank_statements")
    assert extra.status_code == 201  # uploads are open while information is requested
    db.expire_all()
    assert db.get(Application, uuid.UUID(app_id)).status == "NEEDS_INFO"

    clock.advance(minutes=1)
    response = resubmit(client, headers, app_id)

    assert response.status_code == 200
    assert response.json()["current_step"] == "Under assessment"
    assert response.json()["needs_info"] is None
    stored = db.get(Application, uuid.UUID(app_id))
    assert stored.status == "IN_REVIEW" and stored.assigned_officer == officer[0].id
    last = db.scalars(
        select(StatusHistory)
        .where(StatusHistory.application_id == stored.id)
        .order_by(StatusHistory.changed_at.desc())
    ).first()
    assert (last.from_status, last.to_status) == ("NEEDS_INFO", "IN_REVIEW")
    assert "application.resubmit" in db.scalars(select(AuditLog.action)).all()
    assert decide(client, officer[1], app_id, {"outcome": "approve"}).status_code == 201


def resubmit(client, headers, app_id):
    return client.post(f"/applications/{app_id}/resubmit", headers=headers)


def test_lf012_resubmit_is_blocked_while_required_documents_are_missing(client, db, make_user):
    _, headers, app_id = new_application(client, make_user)
    set_status(db, app_id, "NEEDS_INFO")

    response = resubmit(client, headers, app_id)

    assert response.status_code == 409
    assert "Labour contract" in response.json()["detail"]
    db.expire_all()
    assert db.get(Application, uuid.UUID(app_id)).status == "NEEDS_INFO"
    assert outbox(db, app_id) == []


@pytest.mark.parametrize("status", ["SUBMITTED", "IN_REVIEW", "APPROVED", "REFERRED"])
def test_lf012_only_a_file_waiting_for_information_can_be_resubmitted(
    client, db, make_user, status
):
    _, headers, app_id = queued_for(client, make_user)
    set_status(db, app_id, status)

    assert resubmit(client, headers, app_id).status_code == 409


def test_lf012_only_the_owner_can_resubmit(client, db, make_user, officer):
    _, _, app_id = queued_for(client, make_user)
    set_status(db, app_id, "NEEDS_INFO")
    _, stranger = make_user(Role.BORROWER)

    assert resubmit(client, stranger, app_id).status_code == 403
    assert resubmit(client, officer[1], app_id).status_code == 403
    assert resubmit(client, {}, app_id).status_code == 401


# --- AC4: email on every status change -------------------------------------------------------


def test_lf012_each_status_change_queues_one_email_to_the_borrower(
    client, db, make_user, officer, supervisor
):
    owner, headers, app_id = new_application(client, make_user)
    assert outbox(db, app_id) == []  # submission itself is not a status change they asked about

    upload_all(client, headers, app_id)
    decide(client, officer[1], app_id, {"outcome": "request_info", "explanation": ASK})
    resubmit(client, headers, app_id)
    decide(client, officer[1], app_id, {"outcome": "approve"})

    messages = outbox(db, app_id)
    assert [m.template for m in messages] == ["queued", "info_requested", "resubmitted", "approved"]
    assert {m.recipient_user_id for m in messages} == {owner.id}
    assert all(m.subject and m.body for m in messages)


def test_lf012_a_referral_sends_nothing_and_a_rejection_email_has_no_decision_text(
    client, db, make_user, officer, supervisor
):
    _, _, app_id = queued_for(client, make_user)
    before = len(outbox(db, app_id))
    decide(client, officer[1], app_id, {"outcome": "refer"})
    assert len(outbox(db, app_id)) == before

    decide(client, supervisor[1], app_id, reject_body())
    rejected = outbox(db, app_id)[-1]

    assert rejected.template == "rejected"
    assert EXPLANATION not in rejected.body and "INCOME_INSUFFICIENT" not in rejected.body
    assert "Completed" in rejected.body and f"/applications/{app_id}" in rejected.body


def test_lf012_emails_hold_no_amounts_names_or_identity_numbers(client, db, make_user, officer):
    _, _, app_id = queued_for(client, make_user)
    decide(client, officer[1], app_id, {"outcome": "approve"})

    for message in outbox(db, app_id):
        text = f"{message.subject} {message.body}"
        for private in ("100000000", "100,000,000", "Nguyen", "012345678901", "Synthetic Street"):
            assert private not in text


def test_lf012_a_corrected_decision_also_emails_the_borrower(
    client, db, make_user, officer, supervisor
):
    _, _, app_id = queued_for(client, make_user)
    first = decide(client, officer[1], app_id, reject_body()).json()

    decide(client, supervisor[1], app_id, {"outcome": "approve", "supersedes_id": first["id"]})

    assert [m.template for m in outbox(db, app_id)][-2:] == ["rejected", "approved"]


def test_lf012_a_refused_decision_leaves_no_email_behind(client, db, make_user, officer):
    _, _, app_id = queued_for(client, make_user)
    set_status(db, app_id, "IN_REVIEW")
    application = db.get(Application, uuid.UUID(app_id))
    application.exception_flag = True
    db.commit()
    before = len(outbox(db, app_id))

    refused = decide(client, officer[1], app_id, {"outcome": "approve"})

    assert refused.status_code == 403
    assert len(outbox(db, app_id)) == before


def test_lf012_notifications_are_audited_without_their_text(client, db, make_user):
    _, _, app_id = queued_for(client, make_user)

    entries = db.scalars(select(AuditLog).where(AuditLog.action == "notification.queued")).all()

    assert len(entries) == 1 and entries[0].application_id == uuid.UUID(app_id)
    assert entries[0].target_type == "outbox"
