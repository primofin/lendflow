"""LF-003 / LF-004: public loan-terms endpoint exposes configured limits."""

from app.core.config import get_settings


def test_lf003_loan_terms_public_and_matches_settings(client):
    response = client.get("/loan-terms")

    assert response.status_code == 200
    s = get_settings()
    body = response.json()
    assert body["allowed_terms_months"] == sorted(s.allowed_terms_months)
    assert body["amount_min_vnd"] == s.amount_min_vnd
    assert body["amount_max_vnd"] == s.amount_max_vnd
    assert body["purpose_required_from_vnd"] == s.purpose_required_from_vnd


def test_lf003_loan_terms_follow_configuration(client, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "allowed_terms_months", [12, 6])
    monkeypatch.setattr(s, "amount_max_vnd", 300_000_000)

    body = client.get("/loan-terms").json()

    assert body["allowed_terms_months"] == [6, 12]
    assert body["amount_max_vnd"] == 300_000_000
