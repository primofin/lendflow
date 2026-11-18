"""Import every model here so Alembic and tests see the full metadata."""

from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.borrower_profile import BorrowerProfile
from app.models.session import AuthSession
from app.models.user import Role, User

__all__ = ["Application", "AuditLog", "AuthSession", "BorrowerProfile", "Role", "User"]
