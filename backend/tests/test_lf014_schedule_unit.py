"""LF-014 repayment schedule maths (docs/02 worked example) and the month arithmetic."""

from datetime import date

import pytest

from app.core.config import get_settings
from app.core.dates import add_months
from app.services import calculator_service


def test_lf014_worked_example_first_instalment_matches_the_documented_figures():
    rows = calculator_service.schedule(100_000_000, 24)

    assert len(rows) == 24
    assert rows[0].payment_vnd == 4_896_311  # docs/02 worked example
    assert rows[0].interest_vnd == 1_333_333
    assert rows[0].principal_vnd == 4_896_311 - 1_333_333
    assert rows[0].balance_vnd == 100_000_000 - rows[0].principal_vnd


def test_lf014_principal_adds_up_to_the_loan_and_the_balance_ends_at_zero():
    rows = calculator_service.schedule(100_000_000, 24)

    assert sum(r.principal_vnd for r in rows) == 100_000_000
    assert rows[-1].balance_vnd == 0
    assert [r.number for r in rows] == list(range(1, 25))


def test_lf014_last_instalment_absorbs_rounding_within_a_few_vnd():
    rows = calculator_service.schedule(100_000_000, 24)
    quote = calculator_service.quote(100_000_000, 24)

    assert abs(rows[-1].payment_vnd - quote.monthly_payment_vnd) < 50
    assert abs(sum(r.payment_vnd for r in rows) - quote.total_repaid_vnd) < 50


@pytest.mark.parametrize("term", get_settings().allowed_terms_months)
@pytest.mark.parametrize("amount", [1_000_000, 7_654_321, 50_000_000, 500_000_000])
def test_lf014_every_allowed_term_and_amount_gives_a_consistent_schedule(amount, term):
    rows = calculator_service.schedule(amount, term)

    assert len(rows) == term
    assert all(r.payment_vnd == r.principal_vnd + r.interest_vnd for r in rows)
    assert all(r.principal_vnd > 0 and r.interest_vnd >= 0 for r in rows)
    balances = [r.balance_vnd for r in rows]
    assert balances == sorted(balances, reverse=True) and balances[-1] == 0
    assert sum(r.principal_vnd for r in rows) == amount


def test_lf014_interest_falls_and_principal_rises_as_the_balance_shrinks():
    rows = calculator_service.schedule(100_000_000, 24)

    assert rows[0].interest_vnd > rows[10].interest_vnd > rows[-1].interest_vnd
    assert rows[0].principal_vnd < rows[10].principal_vnd


@pytest.mark.parametrize(
    ("start", "months", "expected"),
    [
        (date(2026, 1, 15), 1, date(2026, 2, 15)),
        (date(2026, 1, 31), 1, date(2026, 2, 28)),  # the day is capped at 28
        (date(2026, 11, 18), 2, date(2027, 1, 18)),  # across the year end
        (date(2026, 12, 5), 1, date(2027, 1, 5)),
        (date(2026, 3, 10), 24, date(2028, 3, 10)),
    ],
)
def test_lf014_add_months(start, months, expected):
    assert add_months(start, months) == expected
