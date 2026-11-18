"""Amount and term rules (BR-01, BR-02) shared by the calculator and application submission."""

from app.core.config import get_settings


def check_amount(value: int) -> int:
    settings = get_settings()
    low, high = settings.amount_min_vnd, settings.amount_max_vnd
    if not low <= value <= high:
        raise ValueError(f"Amount must be between {low:,} and {high:,} VND")
    return value


def check_term(value: int) -> int:
    allowed = get_settings().allowed_terms_months
    if value not in allowed:
        raise ValueError(f"Term must be one of {', '.join(map(str, allowed))} months")
    return value
