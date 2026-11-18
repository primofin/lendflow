"""LF-002 authorization policy (docs/01-stakeholders-and-rbac.md). Pure functions, no I/O."""

from decimal import Decimal

from app.core.config import get_settings
from app.core.errors import Forbidden, SupervisorApprovalRequired
from app.models.user import Role

STAFF_ROLES = frozenset({Role.OFFICER, Role.SUPERVISOR})


def check_decision_authority(role: Role, amount_vnd: Decimal, *, exception_flag: bool) -> None:
    """BR-10: officers may decide only below the limit and without exceptions.

    Raises instead of returning a bool so a caller cannot ignore the result.
    Wired into the decision endpoint in LF-011.
    """
    if role == Role.SUPERVISOR:
        return
    if role != Role.OFFICER:
        raise Forbidden()
    if exception_flag or amount_vnd >= get_settings().officer_approval_limit_vnd:
        raise SupervisorApprovalRequired()
