"""Injectable clock so time-based rules (lockout, idle timeout) are testable."""

from collections.abc import Callable
from datetime import UTC, datetime

Clock = Callable[[], datetime]


def utcnow() -> datetime:
    return datetime.now(UTC)


def get_clock() -> Clock:
    return utcnow
