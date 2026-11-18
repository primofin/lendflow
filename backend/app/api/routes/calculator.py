"""LF-003 public loan calculator. No login: prospective borrowers use it before applying."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.schemas.calculator import CalculatorParams, CalculatorQuoteOut
from app.services import calculator_service

router = APIRouter(prefix="/calculator", tags=["calculator"])


@router.get("")
def calculate(params: Annotated[CalculatorParams, Query()]) -> CalculatorQuoteOut:
    """LF-003: monthly payment, total repaid and interest (reducing balance) with the rate used."""
    result = calculator_service.quote(params.amount_vnd, params.term_months)
    return CalculatorQuoteOut(
        amount_vnd=result.amount_vnd,
        term_months=result.term_months,
        method=calculator_service.METHOD,
        annual_rate_percent=float(result.annual_rate * 100),
        monthly_payment_vnd=result.monthly_payment_vnd,
        total_repaid_vnd=result.total_repaid_vnd,
        total_interest_vnd=result.total_interest_vnd,
        first_month_interest_vnd=result.first_month_interest_vnd,
        first_month_principal_vnd=result.first_month_principal_vnd,
    )
