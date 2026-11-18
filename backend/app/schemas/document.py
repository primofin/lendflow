"""LF-005 document schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    doc_type: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime


class UploadNoticeOut(BaseModel):
    notice: str
    allowed_types: list[str]
    max_size_mb: int
