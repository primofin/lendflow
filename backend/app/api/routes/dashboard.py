"""LF-019 operations dashboard. Supervisors only (docs/01 permission matrix)."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import ClientIp, DbSession, Now, SupervisorAuth
from app.schemas.dashboard import DashboardOut, DashboardParams
from app.services import dashboard_service

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def get_dashboard(
    params: Annotated[DashboardParams, Query()],
    auth: SupervisorAuth,
    db: DbSession,
    clock: Now,
    ip: ClientIp,
) -> DashboardOut:
    """LF-019: counts by status, approval rate, average decision time and open SLA breaches."""
    return dashboard_service.summary(
        db,
        viewer=auth.user,
        date_from=params.date_from,
        date_to=params.date_to,
        now=clock(),
        ip=ip,
    )
