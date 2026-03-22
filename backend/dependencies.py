"""FastAPI dependencies for backend services."""

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from backend.services.cache_service import CacheService
from backend.services.db_service import get_db_session
from backend.services.forecast_service import ForecastService
from backend.settings import Settings, get_settings


def get_backend_settings() -> Settings:
    """Returns cached backend settings."""

    return get_settings()


def get_db(session: Session = Depends(get_db_session)) -> Session:
    """Returns the active SQLAlchemy session."""

    return session


def get_cache_service(request: Request) -> CacheService:
    """Returns the app-level cache service."""

    return request.app.state.cache_service


def get_forecast_service(request: Request) -> ForecastService:
    """Returns the app-level forecast service."""

    return request.app.state.forecast_service
