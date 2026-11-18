"""LF-001 Register and log in."""

from fastapi import APIRouter, status

from app.api.deps import ClientIp, CurrentAuth, DbSession, Now
from app.schemas.auth import LoginIn, RefreshIn, RegisterIn, TokenPair, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, db: DbSession, clock: Now, ip: ClientIp) -> TokenPair:
    """LF-001: create a borrower account and log in."""
    return auth_service.register(db, email=body.email, password=body.password, now=clock(), ip=ip)


@router.post("/login")
def login(body: LoginIn, db: DbSession, clock: Now, ip: ClientIp) -> TokenPair:
    """LF-001: log in; five consecutive failures lock the account for 15 minutes."""
    return auth_service.login(db, email=body.email, password=body.password, now=clock(), ip=ip)


@router.post("/refresh")
def refresh(body: RefreshIn, db: DbSession, clock: Now, ip: ClientIp) -> TokenPair:
    """LF-001: exchange a refresh token for a new pair (rotation with reuse detection)."""
    return auth_service.refresh(db, refresh_token=body.refresh_token, now=clock(), ip=ip)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(auth: CurrentAuth, db: DbSession, clock: Now, ip: ClientIp) -> None:
    """LF-001: end the current session."""
    auth_service.logout(db, ctx=auth, now=clock(), ip=ip)


@router.get("/me")
def me(auth: CurrentAuth) -> UserOut:
    """LF-001: the logged-in user."""
    return UserOut.model_validate(auth.user)
