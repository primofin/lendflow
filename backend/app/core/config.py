"""Application settings. All business and security limits are configurable (see docs/02)."""

from functools import lru_cache

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

    ai_mode: str = "mock"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # values come from the environment
