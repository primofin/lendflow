"""audit log: insertion order, application link, append-only triggers

Order matters: add and backfill the columns first, because once the triggers exist no row can
be updated. Downgrading removes the triggers deliberately; that is a conscious schema change,
not something the running application can do.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("audit_logs", sa.Column("application_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_audit_logs_application_id_applications"),
        "audit_logs",
        "applications",
        ["application_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_audit_logs_application_id"), "audit_logs", ["application_id"], unique=False
    )
    op.execute("ALTER TABLE audit_logs ADD COLUMN seq BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL")
    op.create_index(op.f("ix_audit_logs_seq"), "audit_logs", ["seq"], unique=True)

    # Backfill existing rows: entries about an application, and about its documents.
    op.execute(
        """
        UPDATE audit_logs AS a SET application_id = ap.id
        FROM applications AS ap
        WHERE a.target_type = 'application' AND a.target_id = ap.id
        """
    )
    op.execute(
        """
        UPDATE audit_logs AS a SET application_id = d.application_id
        FROM documents AS d
        WHERE a.target_type = 'document' AND a.target_id = d.id
        """
    )

    op.execute(
        """
        CREATE FUNCTION audit_logs_block_change() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'audit_logs is append-only: % is not allowed', TG_OP
                USING ERRCODE = 'restrict_violation';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_logs_no_update_delete
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION audit_logs_block_change()
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_logs_no_truncate
        BEFORE TRUNCATE ON audit_logs
        FOR EACH STATEMENT EXECUTE FUNCTION audit_logs_block_change()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER audit_logs_no_truncate ON audit_logs")
    op.execute("DROP TRIGGER audit_logs_no_update_delete ON audit_logs")
    op.execute("DROP FUNCTION audit_logs_block_change()")
    op.drop_index(op.f("ix_audit_logs_seq"), table_name="audit_logs")
    op.drop_column("audit_logs", "seq")
    op.drop_index(op.f("ix_audit_logs_application_id"), table_name="audit_logs")
    op.drop_constraint(
        op.f("fk_audit_logs_application_id_applications"), "audit_logs", type_="foreignkey"
    )
    op.drop_column("audit_logs", "application_id")
