"""deletion requests (LF-018)

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-18 21:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "deletion_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_deletion_requests_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deletion_requests")),
    )
    op.create_index(op.f("ix_deletion_requests_user_id"), "deletion_requests", ["user_id"])
    op.create_index(
        "uq_deletion_requests_one_open_per_user",
        "deletion_requests",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )


def downgrade() -> None:
    op.drop_table("deletion_requests")
