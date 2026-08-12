from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.error_handlers import register_exception_handlers
from app.api.v1.router import api_router
from app.core.config import Settings, settings
from app.core.database import (
    create_db_engine,
    create_session_factory,
)
from app.core.database import (
    engine as default_engine,
)
from app.core.security import PasswordManager


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        application.state.db_engine.dispose()


def create_app(app_settings: Settings | None = None) -> FastAPI:
    active_settings = app_settings or settings
    application = FastAPI(
        title=active_settings.APP_NAME,
        version=active_settings.APP_VERSION,
        description="Secure File Encryption and Sharing Platform API",
        lifespan=lifespan,
    )
    application.state.settings = active_settings
    application.state.db_engine = (
        default_engine
        if active_settings is settings
        else create_db_engine(
            active_settings.DATABASE_URL,
            connect_args=active_settings.DATABASE_CONNECT_ARGS,
        )
    )
    application.state.db_session_factory = create_session_factory(application.state.db_engine)
    application.state.password_manager = PasswordManager(
        max_concurrent_operations=active_settings.AUTH_PASSWORD_HASH_CONCURRENCY
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.CORS_ORIGINS,
        allow_credentials=active_settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix=active_settings.API_PREFIX)
    register_exception_handlers(application)

    @application.get("/")
    def root():
        return {
            "success": True,
            "message": "Secure File Encryption Platform API is running",
            "docs": "/docs",
        }

    @application.get("/health/live", tags=["Health"])
    def liveness():
        return {"status": "ok"}

    return application


app = create_app()
