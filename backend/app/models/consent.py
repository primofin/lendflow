"""Consent records (BR-21, docs/06 CONSENTS). One row per user and consent version."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Consent(Base):
    __tablename__ = "consents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    consent_version: Mapped[str] = mapped_column(String(32))
    purposes: Mapped[list[str]] = mapped_column(JSON)  # purpose codes accepted
    given_at: Mapped[datetime]
    withdrawn_at: Mapped[datetime | None]  # set by LF-018
