"""LF-004 / BR-21 consent: current text, version check, record keeping."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.consent import CONSENT_VERSION, PURPOSES, STATEMENT
from app.core.errors import UnprocessableEntity
from app.models.consent import Consent
from app.models.user import User
from app.schemas.consent import ConsentOut, PurposeOut


def current_consent() -> ConsentOut:
    return ConsentOut(
        version=CONSENT_VERSION,
        statement=STATEMENT,
        purposes=[PurposeOut(**p) for p in PURPOSES],
        retention_months=get_settings().consent_retention_months,
    )


def require_current_version(version: str) -> None:
    if version != CONSENT_VERSION:
        raise UnprocessableEntity(
            "The consent text has changed. Reload it and accept the current consent."
        )


def record_consent(db: Session, *, user: User, now: datetime) -> bool:
    """Store consent for the current version unless an active one exists. True if created."""
    existing = db.scalar(
        select(Consent.id).where(
            Consent.user_id == user.id,
            Consent.consent_version == CONSENT_VERSION,
            Consent.withdrawn_at.is_(None),
        )
    )
    if existing:
        return False
    db.add(
        Consent(
            user_id=user.id,
            consent_version=CONSENT_VERSION,
            purposes=[p["code"] for p in PURPOSES],
            given_at=now,
        )
    )
    return True
