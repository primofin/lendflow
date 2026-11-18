"""Domain errors mapped to HTTP responses with specific, actionable messages."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code = 400
    detail = "Request could not be processed"
    headers: dict[str, str] | None = None

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.detail)
        if detail:
            self.detail = detail


class NotAuthenticated(AppError):
    status_code = 401
    detail = "Not authenticated. Log in again."
    headers = {"WWW-Authenticate": "Bearer"}  # noqa: RUF012


class InvalidCredentials(NotAuthenticated):
    detail = "Incorrect email or password"


class EmailAlreadyRegistered(AppError):
    status_code = 409
    detail = "This email is already registered"


class AccountLocked(AppError):
    status_code = 423


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            {"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers
        )
