"""LF-003 calculator maths (docs/02: annuity, reducing balance; worked example)."""

from decimal import Decimal

import pytest

from app.core.config import get_settings
from app.services.calculator_service import quote, rate_for_term

ALLOWED_TERMS = [6, 12, 24, 36, 60]


def test_lf003_worked_example_matches_business_rules_doc():
    result = quote(100_000_000, 24)

    assert result.monthly_payment_vnd == 4_896_311
    assert result.total_repaid_vnd == 117_511_465
    assert result.total_interest_vnd == 17_511_465
    assert result.first_month_interest_vnd == 1_333_333
    assert result.first_month_principal_vnd == 3_562_978
    assert result.annual_rate == Decimal("0.16")


@pytest.mark.parametrize(
    ("term", "rate"),
    [(6, "0.14"), (12, "0.14"), (24, "0.16"), (36, "0.16"), (60, "0.18")],
)
def test_lf003_rate_depends_on_term_br05(term, rate):
    assert rate_for_term(term) == Decimal(rate)


def test_lf003_rate_tiers_are_configurable(monkeypatch):
    monkeypatch.setattr(
        get_settings(), "rate_tiers", [(12, Decimal("0.10")), (60, Decimal("0.20"))]
    )

    assert rate_for_term(12) == Decimal("0.10")
    assert rate_for_term(24) == Decimal("0.20")


def test_lf003_term_above_every_tier_is_an_error():
    with pytest.raises(ValueError, match="No interest rate"):
        rate_for_term(120)


@pytest.mark.parametrize("term", ALLOWED_TERMS)
@pytest.mark.parametrize("amount", [1_000_000, 37_654_321, 100_000_000, 500_000_000])
def test_lf003_results_are_whole_vnd_and_consistent(amount, term):
    result = quote(amount, term)

    for value in (
        result.monthly_payment_vnd,
        result.total_repaid_vnd,
        result.total_interest_vnd,
        result.first_month_interest_vnd,
        result.first_month_principal_vnd,
    ):
        assert isinstance(value, int)
    assert result.monthly_payment_vnd > 0
    assert result.total_interest_vnd > 0
    assert result.total_repaid_vnd == amount + result.total_interest_vnd
    # Rounding the monthly payment and the total separately can differ by < term VND.
    assert abs(result.monthly_payment_vnd * term - result.total_repaid_vnd) <= term
    assert (
        result.first_month_interest_vnd + result.first_month_principal_vnd
        == result.monthly_payment_vnd
    )


def test_lf003_longer_term_means_smaller_payment_but_more_interest():
    short, long = quote(100_000_000, 12), quote(100_000_000, 36)

    assert long.monthly_payment_vnd < short.monthly_payment_vnd
    assert long.total_interest_vnd > short.total_interest_vnd


def test_lf003_zero_rate_falls_back_to_straight_division(monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_tiers", [(60, Decimal("0"))])

    result = quote(120_000_000, 12)

    assert result.monthly_payment_vnd == 10_000_000
    assert result.total_interest_vnd == 0
    assert result.first_month_interest_vnd == 0
