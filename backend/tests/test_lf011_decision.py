"""LF-011 Decision with reason code (docs/04; BR-10, BR-12 to BR-15)."""

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.decision import Decision, DecisionImmutable
from app.models.status_history import StatusHistory
from app.models.user import Role

from .test_lf010_queue import queued

EXPLANATION = "Your verified monthly income does not cover the new instalment."
CONDITIONS = "Provide three more months of payslips showing a higher income."


def reject_body(**overrides):
    body = {
        "outcome": "reject",
        "reason_code": "INCOME_INSUFFICIENT",
        "explanation": EXPLANATION,
        "conditions": CONDITIONS,
    }
    return {**body, **overrides}


def decide(client, headers, app_id, body):
    return client.post(f"/applications/{app_id}/decision", headers=headers, json=body)


def app_row(db, app_id):
    db.expire_all()
    return db.get(Application, uuid.UUID(app_id))


def decision_count(db):
    return len(db.scalars(select(Decision)).all())


@pytest.fixture
def officer(make_user):
    return make_user(Role.OFFICER)


@pytest.fixture
def supervisor(make_user):
    return make_user(Role.SUPERVISOR)


# --- AC1: a rejection needs a reason code and an explanation (BR-13) -------------------------


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"reason_code": None}, "reason code"),
        ({"explanation": None}, "explanation"),
        ({"explanation": "no"}, "at least 20 characters"),
        ({"explanation": "   "}, "explanation"),
        ({"conditions": None}, "documents or conditions"),
    ],
)
def test_lf011_rejection_missing_a_required_part_is_blocked(
    client, db, make_user, officer, overrides, expected
):
    app_id = queued(client, make_user, db)

    response = decide(client, officer[1], app_id, reject_body(**overrides))

    assert response.status_code == 422
    assert expected in str(response.json())
    assert decision_count(db) == 0
    assert app_row(db, app_id).status == "IN_REVIEW"


def test_lf011_unknown_reason_code_is_refused_and_lists_the_allowed_ones(
    client, db, make_user, officer
):
    app_id = queued(client, make_user, db)

    response = decide(client, officer[1], app_id, reject_body(reason_code="BECAUSE"))

    assert response.status_code == 422
    assert "BECAUSE" in response.json()["detail"] and "DTI_TOO_HIGH" in response.json()["detail"]
    assert decision_count(db) == 0


def test_lf011_reason_codes_are_listed_for_staff_only(client, make_user, officer):
    _, borrower = make_user(Role.BORROWER)

    codes = client.get("/reason-codes", headers=officer[1])

    assert codes.status_code == 200
    assert "INCOME_INSUFFICIENT" in {c["code"] for c in codes.json()}
    assert client.get("/reason-codes", headers=borrower).status_code == 403


def test_lf011_only_a_rejection_may_carry_a_reason_code(client, db, make_user, officer):
    app_id = queued(client, make_user, db)

    response = decide(
        client, officer[1], app_id, {"outcome": "approve", "reason_code": "OTHER_POLICY"}
    )

    assert response.status_code == 422
    assert "Only a rejection" in str(response.json())


# --- AC2: the borrower sees the explanation and what could change the result -----------------


def test_lf011_borrower_sees_the_rejection_explanation_and_conditions_but_not_the_decider(
    client, db, make_user, officer
):
    _, headers, app_id = new_owned_application(client, make_user, db)

    response = decide(client, officer[1], app_id, reject_body())
    assert response.status_code == 201
    seen = client.get(f"/applications/{app_id}", headers=headers).json()

    assert seen["status"] == "REJECTED"
    assert seen["decision"]["outcome"] == "reject"
    assert seen["decision"]["explanation"] == EXPLANATION
    assert seen["decision"]["conditions"] == CONDITIONS
    assert seen["decision"]["reason_label"]
    assert str(officer[0].id) not in str(seen)


def test_lf011_borrower_cannot_decide_or_list_decisions(client, db, make_user):
    _, headers, app_id = new_owned_application(client, make_user, db)

    assert decide(client, headers, app_id, reject_body()).status_code == 403
    assert client.get(f"/applications/{app_id}/decisions", headers=headers).status_code == 403
    assert app_row(db, app_id).status == "IN_REVIEW"


def new_owned_application(client, make_user, db):
    """Like queued(), but returns the borrower's headers too."""
    from .test_lf010_queue import new_application, upload_all

    owner, headers, app_id = new_application(client, make_user)
    upload_all(client, headers, app_id)
    return owner, headers, app_id


# --- the four outcomes and the state machine -------------------------------------------------


def test_lf011_approve_within_limit_sets_approved_and_records_history_and_audit(
    client, db, make_user, officer
):
    app_id = queued(client, make_user, db)

    response = decide(client, officer[1], app_id, {"outcome": "approve"})

    assert response.status_code == 201 and response.json()["outcome"] == "approve"
    stored = app_row(db, app_id)
    assert stored.status == "APPROVED" and stored.assigned_officer == officer[0].id
    history = db.scalars(
        select(StatusHistory).where(StatusHistory.application_id == stored.id)
    ).all()
    assert (history[-1].from_status, history[-1].to_status) == ("IN_REVIEW", "APPROVED")
    entry = db.scalars(select(AuditLog).where(AuditLog.action == "decision.approve")).one()
    assert entry.actor_id == officer[0].id and entry.application_id == stored.id


def test_lf011_fast_track_approve_needs_one_confirmation_and_no_supervisor(
    client, db, make_user, officer
):
    app_id = queued(client, make_user, db, fast_track=True)

    response = decide(client, officer[1], app_id, {"outcome": "approve"})

    assert response.status_code == 201
    assert app_row(db, app_id).status == "APPROVED"


def test_lf011_request_info_needs_words_and_sets_needs_info(client, db, make_user, officer):
    app_id = queued(client, make_user, db)

    blank = decide(client, officer[1], app_id, {"outcome": "request_info"})
    ok = decide(
        client,
        officer[1],
        app_id,
        {"outcome": "request_info", "explanation": "Please upload your latest bank statement."},
    )

    assert blank.status_code == 422
    assert ok.status_code == 201 and app_row(db, app_id).status == "NEEDS_INFO"


def test_lf011_refer_assigns_a_supervisor_and_hides_the_referral_from_the_borrower(
    client, db, make_user, officer, supervisor
):
    _, headers, app_id = new_owned_application(client, make_user, db)

    response = decide(client, officer[1], app_id, {"outcome": "refer"})

    assert response.status_code == 201
    stored = app_row(db, app_id)
    assert stored.status == "REFERRED" and stored.assigned_supervisor == supervisor[0].id
    assert client.get(f"/applications/{app_id}", headers=headers).json()["decision"] is None


def test_lf011_officer_cannot_decide_a_referred_file_but_a_supervisor_can(
    client, db, make_user, officer, supervisor
):
    app_id = queued(client, make_user, db)
    decide(client, officer[1], app_id, {"outcome": "refer"})

    by_officer = decide(client, officer[1], app_id, {"outcome": "approve"})
    by_supervisor = decide(client, supervisor[1], app_id, {"outcome": "approve"})

    assert by_officer.status_code == 403 and "supervisor" in by_officer.json()["detail"]
    assert by_supervisor.status_code == 201 and app_row(db, app_id).status == "APPROVED"


def test_lf011_supervisor_cannot_refer(client, db, make_user, supervisor):
    app_id = queued(client, make_user, db)

    assert decide(client, supervisor[1], app_id, {"outcome": "refer"}).status_code == 403


@pytest.mark.parametrize("status", ["SUBMITTED", "NEEDS_INFO", "DRAFT"])
def test_lf011_files_not_ready_for_a_decision_give_409(client, db, make_user, officer, status):
    app_id = queued(client, make_user, db)
    application = app_row(db, app_id)
    application.status = status
    db.commit()

    response = decide(client, officer[1], app_id, {"outcome": "approve"})

    assert response.status_code == 409 and status in response.json()["detail"]
    assert decision_count(db) == 0


def test_lf011_a_decided_file_cannot_be_decided_again_without_a_correction(
    client, db, make_user, officer
):
    app_id = queued(client, make_user, db)
    decide(client, officer[1], app_id, {"outcome": "approve"})

    again = decide(client, officer[1], app_id, reject_body())

    assert again.status_code == 409 and "correct" in again.json()["detail"]
    assert decision_count(db) == 1


# --- BR-10: authority limits -----------------------------------------------------------------


def test_lf011_officer_cannot_approve_an_exception_file_or_one_above_the_limit(
    client, db, make_user, officer, supervisor
):
    flagged = queued(client, make_user, db, exception_flag=True)
    large = queued(client, make_user, db, amount_vnd=200_000_000)

    for app_id in (flagged, large):
        response = decide(client, officer[1], app_id, {"outcome": "approve"})
        assert response.status_code == 403
        assert response.json()["detail"] == "Supervisor approval required"
        assert app_row(db, app_id).status == "IN_REVIEW"
    assert decide(client, supervisor[1], flagged, {"outcome": "approve"}).status_code == 201
    assert decide(client, supervisor[1], large, {"outcome": "approve"}).status_code == 201


def test_lf011_officer_may_reject_an_exception_file(client, db, make_user, officer):
    app_id = queued(client, make_user, db, exception_flag=True)

    assert decide(client, officer[1], app_id, reject_body()).status_code == 201


# --- AC4 / BR-14: corrections ----------------------------------------------------------------


def test_lf011_correction_is_a_new_linked_entry_and_the_original_stays_visible(
    client, db, make_user, officer, supervisor
):
    app_id = queued(client, make_user, db)
    first = decide(client, officer[1], app_id, reject_body()).json()

    corrected = decide(
        client,
        supervisor[1],
        app_id,
        {"outcome": "approve", "supersedes_id": first["id"]},
    )

    assert corrected.status_code == 201
    assert app_row(db, app_id).status == "APPROVED"
    entries = client.get(f"/applications/{app_id}/decisions", headers=supervisor[1]).json()
    assert [e["outcome"] for e in entries] == ["reject", "approve"]
    assert entries[0]["explanation"] == EXPLANATION  # original untouched
    assert entries[0]["superseded_by"] == entries[1]["id"]
    assert entries[1]["supersedes_id"] == first["id"]
    assert "decision.correct" in db.scalars(select(AuditLog.action)).all()


def test_lf011_only_a_supervisor_corrects_and_only_the_latest_decision(
    client, db, make_user, officer, supervisor
):
    app_id = queued(client, make_user, db)
    first = decide(client, officer[1], app_id, reject_body()).json()

    by_officer = decide(
        client, officer[1], app_id, {"outcome": "approve", "supersedes_id": first["id"]}
    )
    wrong_target = decide(
        client, supervisor[1], app_id, {"outcome": "approve", "supersedes_id": str(uuid.uuid4())}
    )
    to_request = decide(
        client,
        supervisor[1],
        app_id,
        {
            "outcome": "request_info",
            "explanation": "Please upload your latest bank statement.",
            "supersedes_id": first["id"],
        },
    )

    assert by_officer.status_code == 403
    assert wrong_target.status_code == 409
    assert to_request.status_code == 422
    assert decision_count(db) == 1


def test_lf011_corrected_rejection_still_needs_a_reason_code(
    client, db, make_user, officer, supervisor
):
    app_id = queued(client, make_user, db)
    first = decide(client, officer[1], app_id, {"outcome": "approve"}).json()

    response = decide(
        client,
        supervisor[1],
        app_id,
        {"outcome": "reject", "supersedes_id": first["id"], "explanation": EXPLANATION},
    )

    assert response.status_code == 422


# --- immutability (BR-14) --------------------------------------------------------------------


def test_lf011_database_and_orm_refuse_to_change_or_delete_a_decision(
    client, db, make_user, officer
):
    app_id = queued(client, make_user, db)
    decide(client, officer[1], app_id, reject_body())
    decision = db.scalars(select(Decision)).one()

    for sql in (
        "UPDATE decisions SET outcome = 'approve'",
        "DELETE FROM decisions",
        "TRUNCATE decisions",
    ):
        with pytest.raises(DBAPIError, match="append-only"), db.begin_nested():
            db.execute(text(sql))
    decision.explanation = "tampered"
    with pytest.raises(DecisionImmutable):
        db.flush()
    db.rollback()


# --- BR-15: no automatic decision ------------------------------------------------------------


def test_lf011_files_reach_a_final_status_only_through_a_decision_row(
    client, db, make_user, officer
):
    app_id = queued(client, make_user, db)

    # everything that moves a file (uploads, queue reads, claims, reads) leaves it undecided
    client.get("/queue", headers=officer[1])
    client.post(f"/applications/{app_id}/claim", headers=officer[1])
    client.get(f"/applications/{app_id}", headers=officer[1])
    assert app_row(db, app_id).status == "IN_REVIEW" and decision_count(db) == 0

    decide(client, officer[1], app_id, {"outcome": "approve"})
    final = db.scalars(
        select(Application).where(Application.status.in_(["APPROVED", "REJECTED"]))
    ).all()
    assert len(final) == decision_count(db) == 1


# --- claim and officer scoping ---------------------------------------------------------------


def test_lf011_claiming_assigns_the_file_and_hides_it_from_other_officers(
    client, db, make_user, officer
):
    app_id = queued(client, make_user, db)
    other = make_user(Role.OFFICER)

    first = client.post(f"/applications/{app_id}/claim", headers=officer[1])
    repeat = client.post(f"/applications/{app_id}/claim", headers=officer[1])
    taken = client.post(f"/applications/{app_id}/claim", headers=other[1])

    assert first.status_code == repeat.status_code == 200
    assert app_row(db, app_id).assigned_officer == officer[0].id
    assert taken.status_code == 403
    assert client.get(f"/applications/{app_id}", headers=other[1]).status_code == 403
    assert decide(client, other[1], app_id, {"outcome": "approve"}).status_code == 403
    ids = {i["id"] for i in client.get("/queue", headers=other[1]).json()["items"]}
    assert app_id not in ids
    assert "application.claimed" in db.scalars(select(AuditLog.action)).all()
    denied = db.scalars(
        select(AuditLog).where(
            AuditLog.action == "application.access_denied", AuditLog.actor_id == other[0].id
        )
    ).all()
    assert denied


def test_lf011_supervisor_reads_and_decides_a_file_an_officer_claimed(
    client, db, make_user, officer, supervisor
):
    app_id = queued(client, make_user, db)
    client.post(f"/applications/{app_id}/claim", headers=officer[1])

    assert client.get(f"/applications/{app_id}", headers=supervisor[1]).status_code == 200
    assert decide(client, supervisor[1], app_id, {"outcome": "approve"}).status_code == 201


def test_lf011_only_officers_claim_and_only_in_review_files(
    client, db, make_user, officer, supervisor
):
    app_id = queued(client, make_user, db)
    decide(client, officer[1], app_id, {"outcome": "approve"})
    fresh = queued(client, make_user, db)
    application = app_row(db, fresh)
    application.status = "SUBMITTED"
    db.commit()

    assert client.post(f"/applications/{fresh}/claim", headers=supervisor[1]).status_code == 403
    assert client.post(f"/applications/{fresh}/claim", headers=officer[1]).status_code == 409
    missing = client.post(f"/applications/{uuid.uuid4()}/claim", headers=officer[1])
    assert missing.status_code == 404


def test_lf011_audit_entries_for_decisions_do_not_contain_the_explanation(
    client, db, make_user, officer
):
    app_id = queued(client, make_user, db)
    decide(client, officer[1], app_id, reject_body())

    rows = db.execute(text("SELECT row_to_json(a)::text FROM audit_logs a")).scalars().all()

    assert not any(EXPLANATION in row or CONDITIONS in row for row in rows)
