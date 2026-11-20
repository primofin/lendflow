"""In-memory sliding-window rate limit for the public calculator (D-005).

Per process, which is enough while the API runs as a single instance (it must, because uploads
sit on one volume). Move the counters to a shared store before scaling out.
"""

import time
from collections import deque
from collections.abc import Callable

from fastapi import Request

from app.api.deps import client_ip
from app.core.config import get_settings
from app.core.errors import AppError

_WINDOW_SECONDS = 60.0
_MAX_KEYS = 10_000


class TooManyRequests(AppError):
    status_code = 429

    def __init__(self, retry_after: int) -> None:
        super().__init__(f"Too many requests. Try again in {retry_after} seconds.")
        self.headers = {"Retry-After": str(retry_after)}


class RateLimiter:
    def __init__(self, now: Callable[[], float] = time.monotonic) -> None:
        self._now = now
        self._hits: dict[str, deque[float]] = {}

    def check(self, key: str, limit: int) -> None:
        """Record a hit, or raise TooManyRequests when `key` already made `limit` in a minute."""
        if limit <= 0:
            return
        now = self._now()
        if len(self._hits) >= _MAX_KEYS:
            self._prune(now)
        hits = self._hits.setdefault(key, deque())
        while hits and now - hits[0] >= _WINDOW_SECONDS:
            hits.popleft()
        if len(hits) >= limit:
            raise TooManyRequests(max(1, int(_WINDOW_SECONDS - (now - hits[0])) + 1))
        hits.append(now)

    def _prune(self, now: float) -> None:
        for key in [k for k, h in self._hits.items() if not h or now - h[-1] >= _WINDOW_SECONDS]:
            del self._hits[key]


def limit_calculator(request: Request) -> None:
    limiter: RateLimiter = request.app.state.calculator_limiter
    limiter.check(client_ip(request) or "unknown", get_settings().calculator_rate_limit_per_minute)
