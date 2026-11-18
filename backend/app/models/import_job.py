"""One CSV bulk import (LF-013, docs/06 IMPORT_JOBS). Holds counts only, no row contents."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    file_sha256: Mapped[str] = mapped_column(String(64))  # the filename is deliberately not kept
    total_rows: Mapped[int]
    rows_imported: Mapped[int]
    rows_duplicate: Mapped[int]
    rows_invalid: Mapped[int]
    created_at: Mapped[datetime]
