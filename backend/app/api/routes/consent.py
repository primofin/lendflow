"""LF-004 consent screen content. Public: shown before registration or submission."""

from fastapi import APIRouter

from app.schemas.consent import ConsentOut
from app.services import consent_service

router = APIRouter(prefix="/consent", tags=["consent"])


@router.get("/current")
def current_consent() -> ConsentOut:
    """LF-004: every purpose (credit scoring, AI-assisted processing) and the retention period."""
    return consent_service.current_consent()
