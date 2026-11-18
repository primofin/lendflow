"""LF-003 Loan calculator API. Acceptance criteria: docs/04-user-stories-backlog.md."""

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.application import Application
from app.models.user import Role

from .test_lf004_submit import submit


def calculate(client, amount="100000000", term="24"):
    params = {}
    if amount is not None:
        params["amount_vnd"] = amount
    if term is not None:
        params["term_months"] = term
    return client.get("/calculator", params=params)


def test_lf003_worked_example_without_login(client):
    response = calculate(client)

    assert response.status_code == 200
    body = response.json()
    assert body["monthly_payment_vnd"] == 4_896_311
    assert body["total_repaid_vnd"] == 117_511_465
    assert body["total_interest_vnd"] == 17_511_465


def test_lf003_result_states_method_and_rate_used(client):
    body = calculate(client).json()

    assert body["method"] == "reducing balance"
    assert body["annual_rate_percent"] == 16
    assert body["term_months"] == 24
    assert body["amount_vnd"] == 100_000_000


def test_lf003_money_in_response_is_integer_not_float(client):
    body = calculate(client, amount="37654321", term="36").json()

    for key in ("monthly_payment_vnd", "total_repaid_vnd", "total_interest_vnd", "amount_vnd"):
        assert isinstance(body[key], int), key


@pytest.mark.parametrize("amount", ["1000000", "500000000"])
def test_lf003_amount_boundaries_accepted(client, amount):
    assert calculate(client, amount=amount).status_code == 200


@pytest.mark.parametrize("amount", ["999999", "500000001", "0", "-100"])
def test_lf003_amount_outside_range_rejected_naming_field(client, amount):
    response = calculate(client, amount=amount)

    assert response.status_code == 422
    assert "amount_vnd" in response.text
    assert "between 1,000,000 and 500,000,000 VND" in response.text


@pytest.mark.parametrize("amount", ["abc", "10.5.1", "", "1e9x"])
def test_lf003_non_numeric_amount_rejected_with_message(client, amount):
    response = calculate(client, amount=amount)

    assert response.status_code == 422
    assert "amount_vnd" in response.text


@pytest.mark.parametrize("term", ["5", "18", "48", "120", "x"])
def test_lf003_term_not_in_list_rejected(client, term):
    response = calculate(client, term=term)

    assert response.status_code == 422
    assert "term_months" in response.text


@pytest.mark.parametrize("term", ["6", "12", "24", "36", "60"])
def test_lf003_every_listed_term_accepted(client, term):
    assert calculate(client, term=term).status_code == 200


@pytest.mark.parametrize(("amount", "term"), [(None, "24"), ("100000000", None), (None, None)])
def test_lf003_missing_parameter_rejected(client, amount, term):
    assert calculate(client, amount=amount, term=term).status_code == 422


def test_lf003_validation_errors_do_not_echo_input(client):
    response = calculate(client, amount="secret-looking-value")

    assert "secret-looking-value" not in response.text


# --- Rate stored on submission (decision: snapshot the rate the borrower was quoted) ----


@pytest.mark.parametrize(("term", "rate"), [(12, "0.1400"), (24, "0.1600"), (60, "0.1800")])
def test_lf003_submission_stores_annual_rate_for_term(client, db, make_user, term, rate):
    _, headers = make_user(Role.BORROWER)

    response = submit(client, headers, term_months=term)

    assert response.status_code == 201
    application = db.scalar(select(Application))
    db.refresh(application)
    assert application.annual_rate == Decimal(rate)
    assert response.json()["annual_rate_percent"] == int(float(rate) * 100)
