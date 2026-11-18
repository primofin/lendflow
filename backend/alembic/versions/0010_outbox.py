"""mock email outbox (LF-012)

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-18 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "outbox",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recipient_user_id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("template", sa.String(length=40), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"], ["users.id"], name=op.f("fk_outbox_recipient_user_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_outbox_application_id_applications"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox")),
    )
    op.create_index(op.f("ix_outbox_recipient_user_id"), "outbox", ["recipient_user_id"])
    op.create_index(op.f("ix_outbox_application_id"), "outbox", ["application_id"])


def downgrade() -> None:
    op.drop_table("outbox")
