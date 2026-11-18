"""LendFlow API entry point."""

from fastapi import FastAPI

from app.api.routes import auth
from app.core.errors import register_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(title="LendFlow API", version="0.1.0")
    register_error_handlers(app)
    app.include_router(auth.router)

    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
