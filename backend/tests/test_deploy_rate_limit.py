"""Deployment hardening (decisions log D-005): calculator rate limit and proxy client IP."""

import pytest

from app.core.config import get_settings
from app.core.rate_limit import RateLimiter, TooManyRequests


class Ticker:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def test_limiter_blocks_after_limit_and_frees_after_window():
    ticker = Ticker()
    limiter = RateLimiter(now=ticker)
    for _ in range(3):
        limiter.check("a", 3)
    with pytest.raises(TooManyRequests) as exc:
        limiter.check("a", 3)
    assert exc.value.status_code == 429
    assert 1 <= int(exc.value.headers["Retry-After"]) <= 61
    limiter.check("b", 3)  # other clients are unaffected
    ticker.t += 61
    limiter.check("a", 3)


def test_limiter_zero_disables():
    limiter = RateLimiter()
    for _ in range(500):
        limiter.check("a", 0)


def test_calculator_returns_429_when_over_limit(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "calculator_rate_limit_per_minute", 2)
    params = {"amount_vnd": "100000000", "term_months": "24"}
    assert client.get("/calculator", params=params).status_code == 200
    assert client.get("/calculator", params=params).status_code == 200
    response = client.get("/calculator", params=params)
    assert response.status_code == 429
    assert "Try again in" in response.json()["detail"]
    assert "retry-after" in response.headers


def test_calculator_limit_is_per_client_ip_header(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "calculator_rate_limit_per_minute", 1)
    monkeypatch.setattr(settings, "client_ip_header", "Fly-Client-IP")
    params = {"amount_vnd": "100000000", "term_months": "24"}
    one, two = {"Fly-Client-IP": "203.0.113.1"}, {"Fly-Client-IP": "203.0.113.2"}
    assert client.get("/calculator", params=params, headers=one).status_code == 200
    assert client.get("/calculator", params=params, headers=one).status_code == 429
    assert client.get("/calculator", params=params, headers=two).status_code == 200
