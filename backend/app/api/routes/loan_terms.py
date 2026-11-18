"""LF-003 / LF-004: public loan limits so forms use the real configured values."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(prefix="/loan-terms", tags=["calculator"])


class LoanTermsOut(BaseModel):
    allowed_terms_months: list[int]
    amount_min_vnd: int
    amount_max_vnd: int
    purpose_required_from_vnd: int


@router.get("")
def loan_terms() -> LoanTermsOut:
    """Allowed terms, amount range and the amount from which a purpose is required."""
    s = get_settings()
    return LoanTermsOut(
        allowed_terms_months=sorted(s.allowed_terms_months),
        amount_min_vnd=s.amount_min_vnd,
        amount_max_vnd=s.amount_max_vnd,
        purpose_required_from_vnd=s.purpose_required_from_vnd,
    )
