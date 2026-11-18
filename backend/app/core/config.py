"""Application settings. All business and security limits are configurable (see docs/02)."""

from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://lendflow:lendflow@localhost:5433/lendflow"
    test_database_url: str = "postgresql+psycopg://lendflow:lendflow@localhost:5433/lendflow_test"
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"

    # LF-001 session and password policy
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7
    session_idle_timeout_minutes: int = 30
    password_min_length: int = 10
    login_max_failures: int = 5
    lockout_minutes: int = 15

    # LF-002 / BR-10: officers need a supervisor at or above this amount (illustrative, docs/02)
    officer_approval_limit_vnd: int = 200_000_000

    # LF-004 application rules (BR-01..BR-03, BR-23); illustrative and configurable (docs/02)
    amount_min_vnd: int = 1_000_000
    amount_max_vnd: int = 500_000_000
    allowed_terms_months: list[int] = [6, 12, 24, 36, 60]
    purpose_required_from_vnd: int = 100_000_000  # simplified small-loan rule below this
    min_age_at_application: int = 18
    max_age_at_application: int = 60
    max_age_at_maturity: int = 65
    consent_retention_months: int = 12
    # LF-018 / BR-22: days to answer a deletion request (illustrative, docs/02; configurable)
    deletion_request_due_days: int = 30

    # LF-013 CSV bulk import: size and row limits (configurable)
    import_max_bytes: int = 2 * 1024 * 1024
    import_max_rows: int = 500

    # LF-017 / BR-11: hours a supervisor may take before a file is overdue (illustrative, docs/02)
    supervisor_sla_hours: float = 24

    # LF-003 / BR-05: annual rate by term, as (longest term in months, rate); illustrative.
    # Up to 12 months 14%, 13-36 months 16%, over 36 months 18%.
    rate_tiers: list[tuple[int, Decimal]] = [
        (12, Decimal("0.14")),
        (36, Decimal("0.16")),
        (60, Decimal("0.18")),
    ]

    # LF-005 uploads (BR-24): JPG/PNG/PDF up to 5 MB, stored outside any web root
    storage_dir: Path = Path("storage")
    max_upload_bytes: int = 5 * 1024 * 1024
    max_request_overhead_bytes: int = 64 * 1024  # multipart framing around the file
    max_documents_per_application: int = 20

    # LF-012: where links in notification emails point (the borrower-facing app)
    app_base_url: str = "http://localhost:3000"

    # LF-008 mock CIC: the real bureau takes 3 to 7 minutes; the mock is shorter. Illustrative.
    cic_duration_seconds: int = 20
    cic_attempt_timeout_seconds: int = 60
    cic_max_attempts: int = 2

    ai_mode: str = "mock"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # values come from the environment
