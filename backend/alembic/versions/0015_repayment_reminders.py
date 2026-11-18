"""repayment reminders: opt-out flag and reminder log (LF-014)

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-19 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("repayment_reminders", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.create_table(
        "reminder_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("instalment_number", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_reminder_log_application_id_applications"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reminder_log")),
        sa.UniqueConstraint(
            "application_id", "instalment_number", "kind", name="uq_reminder_log_instalment_kind"
        ),
    )
    op.create_index(op.f("ix_reminder_log_application_id"), "reminder_log", ["application_id"])


def downgrade() -> None:
    op.drop_table("reminder_log")
    op.drop_column("users", "repayment_reminders")
