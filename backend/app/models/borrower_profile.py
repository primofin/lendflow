"""Borrower profile (docs/06 BORROWER_PROFILES). Minimal for LF-002; LF-004 adds fields."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BorrowerProfile(Base):
    __tablename__ = "borrower_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
