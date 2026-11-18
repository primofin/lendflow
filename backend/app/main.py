"""LendFlow API entry point."""

from fastapi import FastAPI

from app.api.routes import applications, audit, auth, calculator, consent, documents, users
from app.core.errors import register_error_handlers
from app.core.request_limits import RequestSizeLimitMiddleware


def create_app() -> FastAPI:
    app = FastAPI(title="LendFlow API", version="0.1.0")
    register_error_handlers(app)
    app.add_middleware(RequestSizeLimitMiddleware)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(consent.router)
    app.include_router(calculator.router)
    app.include_router(documents.router)
    app.include_router(audit.router)
    app.include_router(applications.router)

    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
