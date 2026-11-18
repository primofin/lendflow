"""officer queue (LF-010): high_dti and fast_track flags, queue index

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-18 16:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "applications", sa.Column("high_dti", sa.Boolean(), server_default="false", nullable=False)
    )
    op.add_column(
        "applications",
        sa.Column("fast_track", sa.Boolean(), server_default="false", nullable=False),
    )
    op.create_index(
        "ix_applications_status_submitted_at", "applications", ["status", "submitted_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_applications_status_submitted_at", table_name="applications")
    op.drop_column("applications", "fast_track")
    op.drop_column("applications", "high_dti")
