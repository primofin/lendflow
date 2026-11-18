"""supervisor SLA clock and breach marker (LF-017)

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-18 22:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "applications",
        sa.Column("assigned_supervisor_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "applications", sa.Column("sla_breached_at", sa.DateTime(timezone=True), nullable=True)
    )
    # Files already held by a supervisor: the best known start is when they were submitted.
    op.execute(
        "UPDATE applications SET assigned_supervisor_at = COALESCE(submitted_at, created_at) "
        "WHERE assigned_supervisor IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("applications", "sla_breached_at")
    op.drop_column("applications", "assigned_supervisor_at")
