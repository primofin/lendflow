"""LF-004 Submit application with consent (docs/04; BR-01..BR-04, BR-21)."""

from datetime import date

import pytest
from sqlalchemy import func, select

from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.borrower_profile import BorrowerProfile
from app.models.consent import Consent
from app.models.status_history import StatusHistory
from app.models.user import Role


def years_ago(years: int) -> str:
    """A date of birth making the person `years` old today plus a few days (safe from edges)."""
    today = date.today()
    return date(today.year - years, today.month, 1).isoformat()


def payload(**overrides):
    body = {
        "amount_vnd": 100_000_000,
        "term_months": 24,
        "purpose": "Home renovation",
        "profile": {
            "full_name": "Nguyen Van An",
            "date_of_birth": years_ago(35),
            "national_id": "012345678901",
            "address": "1 Synthetic Street, Hanoi",
            "income_type": "salaried",
            "monthly_income_vnd": 25_000_000,
            "existing_debt_payment_vnd": 0,
        },
        "consent_accepted": True,
        "consent_version": None,  # filled by submit()
    }
    for key, value in overrides.items():
        if key == "profile":
            body["profile"].update(value)
        else:
            body[key] = value
    return body


def submit(client, headers, **overrides):
    body = payload(**overrides)
    if body["consent_version"] is None:
        body["consent_version"] = client.get("/consent/current").json()["version"]
    return client.post("/applications", headers=headers, json=body)


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def nothing_saved(db):
    return (count(db, Application), count(db, BorrowerProfile), count(db, Consent)) == (0, 0, 0)


# --- Consent screen (AC2) ---------------------------------------------------


def test_lf004_consent_screen_lists_purposes_and_retention_without_login(client):
    response = client.get("/consent/current")

    assert response.status_code == 200
    body = response.json()
    assert body["version"]
    purposes = " ".join(p["label"].lower() for p in body["purposes"])
    assert "credit scoring" in purposes
    assert "ai-assisted document processing" in purposes
    assert body["retention_months"] == 12


# --- Success (AC3) ------------------------------------------------------------


def test_lf004_valid_submission_creates_submitted_application_with_consent(client, db, make_user):
    borrower, headers = make_user(Role.BORROWER)

    response = submit(client, headers)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "SUBMITTED"
    assert body["amount_vnd"] == 100_000_000
    assert isinstance(body["amount_vnd"], int)
    assert body["submitted_at"]
    consent = db.scalar(select(Consent).where(Consent.user_id == borrower.id))
    assert consent.consent_version == client.get("/consent/current").json()["version"]
    assert consent.given_at is not None and consent.withdrawn_at is None
    history = db.scalars(select(StatusHistory)).all()
    assert [(h.from_status, h.to_status, h.actor_id) for h in history] == [
        ("DRAFT", "SUBMITTED", borrower.id)
    ]
    actions = db.scalars(select(AuditLog.action).where(AuditLog.actor_id == borrower.id)).all()
    assert {"application.submit", "consent.give"} <= set(actions)


def test_lf004_borrower_can_read_back_own_submitted_application(client, make_user):
    _, headers = make_user(Role.BORROWER)
    created = submit(client, headers).json()

    response = client.get(f"/applications/{created['id']}", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "SUBMITTED"


def test_lf004_national_id_is_not_written_to_audit_log(client, db, make_user):
    _, headers = make_user(Role.BORROWER)
    submit(client, headers)

    for row in db.scalars(select(AuditLog)).all():
        assert "012345678901" not in repr(vars(row))


# --- Consent blocks submission (AC1, BR-21) ----------------------------------


@pytest.mark.parametrize(
    "overrides",
    [
        {"consent_accepted": False},
        {"consent_version": "stale-version"},
    ],
)
def test_lf004_submission_blocked_without_valid_consent_and_nothing_saved(
    client, db, make_user, overrides
):
    _, headers = make_user(Role.BORROWER)

    response = submit(client, headers, **overrides)

    assert response.status_code == 422
    assert "consent" in response.text.lower()
    assert nothing_saved(db)


def test_lf004_missing_consent_fields_rejected_and_nothing_saved(client, db, make_user):
    _, headers = make_user(Role.BORROWER)
    body = payload()
    del body["consent_accepted"], body["consent_version"]

    response = client.post("/applications", headers=headers, json=body)

    assert response.status_code == 422
    assert nothing_saved(db)


# --- Amount and term (AC4, BR-01, BR-02) ---------------------------------------


@pytest.mark.parametrize("amount", [999_999, 500_000_001, 0, -5])
def test_lf004_amount_outside_range_rejected_nothing_saved(client, db, make_user, amount):
    _, headers = make_user(Role.BORROWER)

    response = submit(client, headers, amount_vnd=amount)

    assert response.status_code == 422
    assert "amount_vnd" in response.text
    assert nothing_saved(db)


@pytest.mark.parametrize("amount", [1_000_000, 500_000_000])
def test_lf004_amount_at_range_boundaries_accepted(client, make_user, amount):
    _, headers = make_user(Role.BORROWER)

    assert submit(client, headers, amount_vnd=amount).status_code == 201


@pytest.mark.parametrize("term", [0, 5, 18, 48, 61])
def test_lf004_term_not_in_list_rejected(client, db, make_user, term):
    _, headers = make_user(Role.BORROWER)

    response = submit(client, headers, term_months=term)

    assert response.status_code == 422
    assert "term_months" in response.text
    assert nothing_saved(db)


@pytest.mark.parametrize("term", [6, 12, 24, 36, 60])
def test_lf004_every_listed_term_accepted(client, make_user, term):
    _, headers = make_user(Role.BORROWER)

    assert submit(client, headers, term_months=term).status_code == 201


# --- Small-loan purpose rule (AC5) ------------------------------------------------


def test_lf004_blank_purpose_accepted_below_100m(client, make_user):
    _, headers = make_user(Role.BORROWER)

    assert submit(client, headers, amount_vnd=99_999_999, purpose="").status_code == 201


@pytest.mark.parametrize("purpose", ["", "   ", None])
def test_lf004_blank_purpose_rejected_at_100m_or_more(client, db, make_user, purpose):
    _, headers = make_user(Role.BORROWER)

    response = submit(client, headers, amount_vnd=100_000_000, purpose=purpose)

    assert response.status_code == 422
    assert "purpose" in response.text
    assert nothing_saved(db)


def test_lf004_small_loan_threshold_is_configurable(client, make_user, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "purpose_required_from_vnd", 50_000_000)
    _, headers = make_user(Role.BORROWER)

    assert submit(client, headers, amount_vnd=60_000_000, purpose="").status_code == 422


# --- Profile rules (BR-03, BR-04) ---------------------------------------------------


@pytest.mark.parametrize(
    "national_id", ["123456789", "12345678901", "0123456789012", "12345678901a"]
)
def test_lf004_national_id_must_be_12_digits(client, db, make_user, national_id):
    _, headers = make_user(Role.BORROWER)

    response = submit(client, headers, profile={"national_id": national_id})

    assert response.status_code == 422
    assert "National ID must be 12 digits" in response.text
    assert nothing_saved(db)


def test_lf004_applicant_under_18_rejected(client, db, make_user):
    _, headers = make_user(Role.BORROWER)

    response = submit(client, headers, profile={"date_of_birth": years_ago(17)})

    assert response.status_code == 422
    assert "18" in response.text
    assert nothing_saved(db)


def test_lf004_applicant_over_60_rejected(client, db, make_user):
    _, headers = make_user(Role.BORROWER)

    response = submit(client, headers, profile={"date_of_birth": years_ago(61)})

    assert response.status_code == 422
    assert "60" in response.text
    assert nothing_saved(db)


def test_lf004_age_at_maturity_limit_enforced_and_configurable(client, db, make_user, monkeypatch):
    from app.core.config import get_settings

    # With the documented ranges (max 60 + 60 months = 65) the limit cannot trip, so lower it.
    monkeypatch.setattr(get_settings(), "max_age_at_maturity", 62)
    _, headers = make_user(Role.BORROWER)

    too_old = submit(client, headers, profile={"date_of_birth": years_ago(60)}, term_months=36)
    ok = submit(client, headers, profile={"date_of_birth": years_ago(60)}, term_months=12)

    assert too_old.status_code == 422
    assert "maturity" in too_old.text
    assert ok.status_code == 201
    assert count(db, Application) == 1


def test_lf004_unknown_income_type_rejected(client, db, make_user):
    _, headers = make_user(Role.BORROWER)

    response = submit(client, headers, profile={"income_type": "lottery"})

    assert response.status_code == 422
    assert nothing_saved(db)


# --- Roles ------------------------------------------------------------------------


@pytest.mark.parametrize("role", [Role.OFFICER, Role.SUPERVISOR])
def test_lf004_staff_cannot_submit_applications(client, db, make_user, role):
    _, headers = make_user(role)

    response = submit(client, headers)

    assert response.status_code == 403
    assert nothing_saved(db)


def test_lf004_unauthenticated_submit_401(client):
    body = payload(consent_version="x")

    assert client.post("/applications", json=body).status_code == 401


# --- Repeat applications ----------------------------------------------------------


def test_lf004_second_application_reuses_profile_and_consent(client, db, make_user):
    _, headers = make_user(Role.BORROWER)

    first = submit(client, headers)
    second = submit(client, headers, amount_vnd=50_000_000, profile={"address": "2 New Street"})

    assert first.status_code == second.status_code == 201
    assert count(db, Application) == 2
    assert count(db, BorrowerProfile) == 1
    assert count(db, Consent) == 1
    assert db.scalar(select(BorrowerProfile.address)) == "2 New Street"


def test_lf004_validation_errors_do_not_echo_personal_data(client, make_user):
    _, headers = make_user(Role.BORROWER)

    # A model-level error (missing consent) is the case where FastAPI echoes the whole body.
    response = submit(
        client, headers, consent_accepted=False, profile={"full_name": "Echo Check Person"}
    )

    assert response.status_code == 422
    assert "012345678901" not in response.text
    assert "Echo Check Person" not in response.text
    assert "consent" in response.text.lower()  # the reason is still reported
