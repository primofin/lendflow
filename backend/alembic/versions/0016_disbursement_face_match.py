"""disbursements (append-only) and simulated face matches (LF-020)

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-19 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "face_matches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("performed_by", sa.Uuid(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_face_matches_application_id_applications"),
        ),
        sa.ForeignKeyConstraint(
            ["performed_by"], ["users.id"], name=op.f("fk_face_matches_performed_by_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_face_matches")),
    )
    op.create_index(op.f("ix_face_matches_application_id"), "face_matches", ["application_id"])
    op.create_table(
        "disbursements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("seq", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("amount_vnd", sa.Numeric(18, 0), nullable=False),
        sa.Column("disbursed_by", sa.Uuid(), nullable=False),
        sa.Column("face_match_id", sa.Uuid(), nullable=True),
        sa.Column("disbursed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_disbursements_application_id_applications"),
        ),
        sa.ForeignKeyConstraint(
            ["disbursed_by"], ["users.id"], name=op.f("fk_disbursements_disbursed_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["face_match_id"],
            ["face_matches.id"],
            name=op.f("fk_disbursements_face_match_id_face_matches"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_disbursements")),
        sa.UniqueConstraint("application_id", name=op.f("uq_disbursements_application_id")),
    )
    op.create_index(op.f("ix_disbursements_seq"), "disbursements", ["seq"], unique=True)
    op.execute(
        """
        CREATE FUNCTION disbursements_block_change() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'disbursements is append-only: % is not allowed', TG_OP
                USING ERRCODE = 'restrict_violation';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER disbursements_no_update_delete
        BEFORE UPDATE OR DELETE ON disbursements
        FOR EACH ROW EXECUTE FUNCTION disbursements_block_change()
        """
    )
    op.execute(
        """
        CREATE TRIGGER disbursements_no_truncate
        BEFORE TRUNCATE ON disbursements
        FOR EACH STATEMENT EXECUTE FUNCTION disbursements_block_change()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER disbursements_no_truncate ON disbursements")
    op.execute("DROP TRIGGER disbursements_no_update_delete ON disbursements")
    op.execute("DROP FUNCTION disbursements_block_change()")
    op.drop_table("disbursements")
    op.drop_table("face_matches")
