"""Import every model here so Alembic and tests see the full metadata."""

from app.models.application import Application, ApplicationStatus
from app.models.audit_log import AuditLog
from app.models.borrower_profile import BorrowerProfile, IncomeType
from app.models.consent import Consent
from app.models.session import AuthSession
from app.models.status_history import StatusHistory
from app.models.user import Role, User

__all__ = [
    "Application",
    "ApplicationStatus",
    "AuditLog",
    "AuthSession",
    "BorrowerProfile",
    "Consent",
    "IncomeType",
    "Role",
    "StatusHistory",
    "User",
]
