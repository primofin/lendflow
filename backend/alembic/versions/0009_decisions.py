"""decisions and reason codes (LF-011)

Creates the append-only decisions table (triggers reject UPDATE, DELETE and TRUNCATE for every
connection, as for audit_logs) and the reason_codes table, seeded with ILLUSTRATIVE codes. The
real list is an open item for Compliance (Q6).

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-18 17:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_REASON_CODES = [
    ("INCOME_INSUFFICIENT", "Verified income is not enough for the requested loan"),
    ("DTI_TOO_HIGH", "Existing debt payments plus the new instalment are too high for the income"),
    ("CREDIT_HISTORY", "Credit history does not meet the lending policy"),
    ("DOCUMENTS_INCOMPLETE", "Required documents were not provided"),
    ("DOCUMENTS_INCONSISTENT", "Documents do not match each other or the application"),
    ("AGE_OR_TERM_LIMIT", "Applicant age and loan term do not fit the lending policy"),
    ("OTHER_POLICY", "Another lending policy requirement is not met"),
]


def upgrade() -> None:
    reason_codes = op.create_table(
        "reason_codes",
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("label", sa.String(length=150), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_reason_codes")),
    )
    op.bulk_insert(
        reason_codes,
        [
            {"code": code, "label": label, "sort_order": index, "active": True}
            for index, (code, label) in enumerate(_REASON_CODES, start=1)
        ],
    )
    op.create_table(
        "decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("seq", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("decided_by", sa.Uuid(), nullable=False),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.Column("reason_code", sa.String(length=40), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("conditions", sa.Text(), nullable=True),
        sa.Column("supersedes_id", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_decisions_application_id_applications"),
        ),
        sa.ForeignKeyConstraint(
            ["decided_by"], ["users.id"], name=op.f("fk_decisions_decided_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["reason_code"],
            ["reason_codes.code"],
            name=op.f("fk_decisions_reason_code_reason_codes"),
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_id"], ["decisions.id"], name=op.f("fk_decisions_supersedes_id_decisions")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_decisions")),
    )
    op.create_index(op.f("ix_decisions_seq"), "decisions", ["seq"], unique=True)
    op.create_index(op.f("ix_decisions_application_id"), "decisions", ["application_id"])
    op.execute(
        """
        CREATE FUNCTION decisions_block_change() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'decisions is append-only: % is not allowed', TG_OP
                USING ERRCODE = 'restrict_violation';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER decisions_no_update_delete
        BEFORE UPDATE OR DELETE ON decisions
        FOR EACH ROW EXECUTE FUNCTION decisions_block_change()
        """
    )
    op.execute(
        """
        CREATE TRIGGER decisions_no_truncate
        BEFORE TRUNCATE ON decisions
        FOR EACH STATEMENT EXECUTE FUNCTION decisions_block_change()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER decisions_no_truncate ON decisions")
    op.execute("DROP TRIGGER decisions_no_update_delete ON decisions")
    op.execute("DROP FUNCTION decisions_block_change()")
    op.drop_table("decisions")
    op.drop_table("reason_codes")
