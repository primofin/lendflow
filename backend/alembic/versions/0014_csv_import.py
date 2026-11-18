"""CSV bulk import: import jobs, profiles without an account (LF-013)

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-18 23:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "import_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("rows_imported", sa.Integer(), nullable=False),
        sa.Column("rows_duplicate", sa.Integer(), nullable=False),
        sa.Column("rows_invalid", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_import_jobs_created_by_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_jobs")),
    )
    op.create_index(op.f("ix_import_jobs_created_by"), "import_jobs", ["created_by"])

    op.alter_column("borrower_profiles", "user_id", existing_type=sa.Uuid(), nullable=True)
    op.add_column(
        "borrower_profiles", sa.Column("contact_email", sa.String(length=320), nullable=True)
    )
    # An imported profile is found again by its email until the borrower has an account.
    op.create_index(
        "uq_borrower_profiles_unclaimed_email",
        "borrower_profiles",
        ["contact_email"],
        unique=True,
        postgresql_where=sa.text("user_id IS NULL"),
    )

    op.add_column("applications", sa.Column("import_job_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        op.f("fk_applications_import_job_id_import_jobs"),
        "applications",
        "import_jobs",
        ["import_job_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_applications_import_job_id_import_jobs"), "applications", type_="foreignkey"
    )
    op.drop_column("applications", "import_job_id")
    op.drop_index("uq_borrower_profiles_unclaimed_email", table_name="borrower_profiles")
    op.drop_column("borrower_profiles", "contact_email")
    op.alter_column("borrower_profiles", "user_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_table("import_jobs")
