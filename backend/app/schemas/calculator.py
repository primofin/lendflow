"""LF-003 calculator request and response."""

from pydantic import BaseModel, field_validator

from app.schemas.loan_terms import check_amount, check_term


class CalculatorParams(BaseModel):
    amount_vnd: int
    term_months: int

    _amount_in_range = field_validator("amount_vnd")(check_amount)
    _term_allowed = field_validator("term_months")(check_term)


class CalculatorQuoteOut(BaseModel):
    amount_vnd: int
    term_months: int
    method: str
    annual_rate_percent: float  # display value (e.g. 16.0); not used for any calculation
    monthly_payment_vnd: int
    total_repaid_vnd: int
    total_interest_vnd: int
    first_month_interest_vnd: int
    first_month_principal_vnd: int
