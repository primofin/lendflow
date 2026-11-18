"""mock CIC checks (LF-008)

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-18 20:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cic_checks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("started_by", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("debt_group", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "debt_group IS NULL OR debt_group BETWEEN 1 AND 5",
            name=op.f("ck_cic_checks_debt_group_range"),
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_cic_checks_application_id_applications"),
        ),
        sa.ForeignKeyConstraint(
            ["started_by"], ["users.id"], name=op.f("fk_cic_checks_started_by_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cic_checks")),
    )
    op.create_index(op.f("ix_cic_checks_application_id"), "cic_checks", ["application_id"])


def downgrade() -> None:
    op.drop_table("cic_checks")
