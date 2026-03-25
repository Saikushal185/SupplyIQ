"""FastAPI dependencies for backend services."""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.cache_service import CacheService
from backend.services.db_service import get_db_session
from backend.services.forecast_service import ForecastService
from backend.settings import Settings, get_settings


def get_backend_settings() -> Settings:
    """Returns cached backend settings."""

    return get_settings()


async def get_db(session: AsyncSession = Depends(get_db_session)) -> AsyncSession:
    """Returns the active SQLAlchemy session."""

    return session


def get_cache_service(request: Request) -> CacheService:
    """Returns the app-level cache service."""

    return request.app.state.cache_service


def get_forecast_service(request: Request) -> ForecastService:
    """Returns the app-level forecast service."""

    return request.app.state.forecast_service


def _extract_email_candidate(value: object) -> str | None:
    """Normalizes different Clerk principal email shapes into a single email string."""

    if isinstance(value, str) and "@" in value:
        return value
    if isinstance(value, dict):
        for key in ("email_address", "email", "address"):
            candidate = _extract_email_candidate(value.get(key))
            if candidate is not None:
                return candidate
        return None
    if isinstance(value, list):
        for item in value:
            candidate = _extract_email_candidate(item)
            if candidate is not None:
                return candidate
    return None


def get_current_user_email(request: Request) -> str | None:
    """Returns the authenticated user's email when auth is enabled and available."""

    principal = getattr(request.state, "principal", None)
    if not isinstance(principal, dict):
        return None

    for key in ("email", "email_address", "primary_email_address", "primary_email"):
        candidate = _extract_email_candidate(principal.get(key))
        if candidate is not None:
            return candidate

    return _extract_email_candidate(principal.get("email_addresses"))
