"""LF-003 loan calculator: annuity, reducing balance (docs/02-business-rules.md).

    r   = annual_rate / 12
    PMT = P * r / (1 - (1 + r) ** -n)

Money is Decimal throughout, never float, and results are whole VND. Rounding rule (follows
the documented worked example): the monthly payment and the total repaid are each rounded
once from the exact figures, so total = round(exact PMT * n), not round(PMT) * n. The two can
differ by a few VND; a repayment schedule (a later story) is where instalments get adjusted.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, localcontext

from app.core.config import get_settings

METHOD = "reducing balance"


@dataclass(frozen=True)
class Quote:
    amount_vnd: int
    term_months: int
    annual_rate: Decimal
    monthly_payment_vnd: int
    total_repaid_vnd: int
    total_interest_vnd: int
    first_month_interest_vnd: int
    first_month_principal_vnd: int


def rate_for_term(term_months: int) -> Decimal:
    """BR-05: the annual rate for a term, from the configurable tiers."""
    for longest_term, rate in sorted(get_settings().rate_tiers):
        if term_months <= longest_term:
            return rate
    raise ValueError(f"No interest rate is configured for a {term_months}-month term")


def _whole_vnd(value: Decimal) -> int:
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def quote(amount_vnd: int, term_months: int) -> Quote:
    rate = rate_for_term(term_months)
    with localcontext() as ctx:
        ctx.prec = 50  # far more than needed for VND amounts; avoids drift in (1 + r) ** -n
        principal = Decimal(amount_vnd)
        monthly_rate = rate / 12
        if monthly_rate == 0:
            payment = principal / term_months
        else:
            payment = principal * monthly_rate / (1 - (1 + monthly_rate) ** -term_months)
        monthly = _whole_vnd(payment)
        total = _whole_vnd(payment * term_months)
        first_interest = _whole_vnd(principal * monthly_rate)
    return Quote(
        amount_vnd=amount_vnd,
        term_months=term_months,
        annual_rate=rate,
        monthly_payment_vnd=monthly,
        total_repaid_vnd=total,
        total_interest_vnd=total - amount_vnd,
        first_month_interest_vnd=first_interest,
        first_month_principal_vnd=monthly - first_interest,
    )
