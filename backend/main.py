"""FastAPI entrypoint for SupplyIQ."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.middleware.auth import ClerkAuthMiddleware, ClerkTokenVerifier
from backend.routers import analytics, forecast, inventory
from backend.services.cache_service import CacheService
from backend.services.db_service import dispose_database_engine, initialize_database
from backend.services.forecast_service import ForecastService
from backend.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes database state and startup services."""

    settings = get_settings()
    await initialize_database()
    app.state.cache_service = CacheService()
    app.state.forecast_service = ForecastService()
    logger.info("SupplyIQ backend initialized.")
    try:
        yield
    finally:
        await app.state.cache_service.close()
        await dispose_database_engine()


def create_app() -> FastAPI:
    """Creates and configures the FastAPI application."""

    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan, version="1.0.0")
    app.add_middleware(
        ClerkAuthMiddleware,
        enabled=settings.auth_enabled,
        verifier=(
            ClerkTokenVerifier(
                jwks_url=settings.clerk_jwks_url,
                issuer=settings.clerk_issuer,
                audience=settings.clerk_audience,
                cache_ttl_seconds=settings.clerk_jwks_cache_ttl_seconds,
            )
            if settings.auth_enabled and settings.clerk_jwks_url
            else None
        ),
        public_paths={
            "/",
            f"{settings.api_prefix}/health",
            "/docs",
            "/openapi.json",
            "/redoc",
        },
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get(f"{settings.api_prefix}/health")
    async def health() -> JSONResponse:
        """Returns a lightweight health response for orchestration checks."""

        return JSONResponse({"status": "ok"})

    app.include_router(analytics.router, prefix=settings.api_prefix)
    app.include_router(forecast.router, prefix=settings.api_prefix)
    app.include_router(inventory.router, prefix=settings.api_prefix)
    return app


app = create_app()
