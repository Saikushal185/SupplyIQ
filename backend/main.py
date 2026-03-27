"""FastAPI entrypoint for SupplyIQ."""

from __future__ import annotations

import inspect
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.middleware.auth import ClerkAuthMiddleware, ClerkTokenVerifier
from backend.routers import analytics, forecast, inventory, pipeline
from backend.services.cache_service import CacheService
from backend.services.db_service import SessionLocal, dispose_database_engine, engine, initialize_database
from backend.services.forecast_service import ForecastService
from backend.services.response_service import build_response
from backend.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes database state and startup services."""

    await initialize_database()
    app.state.cache_service = CacheService()
    app.state.forecast_service = ForecastService()
    logger.info("SupplyIQ backend initialized.")
    try:
        yield
    finally:
        cache_service = getattr(app.state, "cache_service", None)
        if cache_service is not None:
            close_result = cache_service.close()
            if inspect.isawaitable(close_result):
                await close_result
        await dispose_database_engine()


async def check_database_connection() -> bool:
    """Returns whether the backing PostgreSQL database is reachable."""

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:  # pragma: no cover - surfaced as a bool in health.
        logger.exception("Database health check failed.")
        return False


async def check_redis_connection(cache_service: CacheService) -> bool:
    """Returns whether the backing Redis cache is reachable."""

    try:
        return await cache_service.ping()
    except Exception:  # pragma: no cover - surfaced as a bool in health.
        logger.exception("Redis health check failed.")
        return False


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
            f"{settings.api_prefix}/health",
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
    async def health():
        """Returns API, database, and cache health in the shared response envelope."""

        cache_service = getattr(app.state, "cache_service", None) or CacheService()
        db_ok, redis_ok = await check_database_connection(), await check_redis_connection(cache_service)
        return build_response(
            {
                "status": "ok",
                "db": db_ok,
                "redis": redis_ok,
            }
        )

    app.include_router(analytics.router, prefix=settings.api_prefix)
    app.include_router(forecast.router, prefix=settings.api_prefix)
    app.include_router(inventory.router, prefix=settings.api_prefix)
    app.include_router(pipeline.router, prefix=settings.api_prefix)
    return app


app = create_app()
