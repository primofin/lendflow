"""LF-007 migration 0007 round-trip on a scratch database: the seeded rules survive."""

from alembic import command
from sqlalchemy import create_engine, text

from .test_lf016_migration import alembic_config, scratch_url  # noqa: F401  (fixture)

COUNTS = {
    "income_type_rules": "SELECT count(*) FROM income_type_rules",
    "required_document_rules": "SELECT count(*) FROM required_document_rules",
    "required_document_options": "SELECT count(*) FROM required_document_options",
}


def count(conn, table):
    return conn.execute(text(COUNTS[table])).scalar()


def test_lf007_upgrade_downgrade_upgrade_keeps_the_seeded_rules(scratch_url):  # noqa: F811
    cfg = alembic_config(scratch_url)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "0006")
    command.upgrade(cfg, "head")

    engine = create_engine(scratch_url)
    with engine.connect() as conn:
        assert count(conn, "income_type_rules") == 5
        assert count(conn, "required_document_rules") == 19
        assert count(conn, "required_document_options") == 21
    engine.dispose()
