"""LF-002 user management. Supervisor only; enforced here, not just hidden in the UI."""

import uuid

from fastapi import APIRouter, status

from app.api.deps import ClientIp, DbSession, Now, SupervisorAuth
from app.schemas.user import RoleChangeIn, UserAdminOut, UserCreateIn
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
def list_users(auth: SupervisorAuth, db: DbSession) -> list[UserAdminOut]:
    """LF-002: list all users."""
    return [UserAdminOut.model_validate(u) for u in user_service.list_users(db)]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreateIn, auth: SupervisorAuth, db: DbSession, clock: Now, ip: ClientIp
) -> UserAdminOut:
    """LF-002: create a user with any role."""
    user = user_service.create_user(
        db,
        actor=auth.user,
        email=body.email,
        password=body.password,
        role=body.role,
        now=clock(),
        ip=ip,
    )
    return UserAdminOut.model_validate(user)


@router.patch("/{user_id}/role")
def change_role(
    user_id: uuid.UUID,
    body: RoleChangeIn,
    auth: SupervisorAuth,
    db: DbSession,
    clock: Now,
    ip: ClientIp,
) -> UserAdminOut:
    """LF-002: assign a role. Supervisors cannot change their own role."""
    user = user_service.change_role(
        db, actor=auth.user, user_id=user_id, role=body.role, now=clock(), ip=ip
    )
    return UserAdminOut.model_validate(user)
