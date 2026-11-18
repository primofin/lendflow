"""LF-002 AC2 / BR-10: officer approval limit. Wired to the decision endpoint in LF-011."""

from decimal import Decimal

import pytest

from app.core.errors import Forbidden, SupervisorApprovalRequired
from app.core.permissions import check_decision_authority
from app.models.user import Role

LIMIT = 200_000_000


def test_lf002_officer_can_decide_below_limit():
    check_decision_authority(Role.OFFICER, Decimal(199_999_999), exception_flag=False)


@pytest.mark.parametrize("amount", [LIMIT, LIMIT + 1, 1_000_000_000])
def test_lf002_officer_cannot_approve_at_or_above_200m(amount):
    with pytest.raises(SupervisorApprovalRequired) as exc:
        check_decision_authority(Role.OFFICER, Decimal(amount), exception_flag=False)

    assert exc.value.detail == "Supervisor approval required"


def test_lf002_officer_cannot_approve_exception_case():
    with pytest.raises(SupervisorApprovalRequired):
        check_decision_authority(Role.OFFICER, Decimal(10_000_000), exception_flag=True)


@pytest.mark.parametrize("exception_flag", [False, True])
def test_lf002_supervisor_can_approve_above_limit(exception_flag):
    check_decision_authority(Role.SUPERVISOR, Decimal(5_000_000_000), exception_flag=exception_flag)


def test_lf002_borrower_can_never_decide():
    with pytest.raises(Forbidden):
        check_decision_authority(Role.BORROWER, Decimal(1), exception_flag=False)


def test_lf002_limit_is_configurable(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "officer_approval_limit_vnd", 50_000_000)

    with pytest.raises(SupervisorApprovalRequired):
        check_decision_authority(Role.OFFICER, Decimal(50_000_000), exception_flag=False)
