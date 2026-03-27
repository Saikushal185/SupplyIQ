"""FastAPI dependencies for backend services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.cache_service import CacheService
from backend.services.db_service import get_db_session
from backend.services.forecast_service import ForecastService
from backend.settings import Settings, get_settings

UserRole = Literal["admin", "analyst", "viewer"]


@dataclass(slots=True)
class AuthContext:
    """Represents the authenticated Clerk principal for a request."""

    user_id: str
    role: UserRole
    claims: dict[str, Any]


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


def _normalize_user_role(value: object) -> UserRole:
    """Normalizes the supported Clerk role values."""

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"admin", "analyst", "viewer"}:
            return normalized  # type: ignore[return-value]
    return "viewer"


def _extract_public_metadata(principal: dict[str, Any]) -> dict[str, Any]:
    """Returns the Clerk public metadata payload when present."""

    for key in ("public_metadata", "publicMetadata"):
        value = principal.get(key)
        if isinstance(value, dict):
            return value
    return {}


def get_auth_context(request: Request) -> AuthContext:
    """Returns the active authentication context extracted by middleware."""

    principal = getattr(request.state, "principal", None)
    user_id = getattr(request.state, "user_id", None)
    role = getattr(request.state, "role", None)

    if not isinstance(principal, dict) or not isinstance(user_id, str) or not user_id:
        raise HTTPException(status_code=401, detail="Authentication context is missing.")

    return AuthContext(
        user_id=user_id,
        role=_normalize_user_role(role),
        claims=principal,
    )


def require_roles(*allowed_roles: UserRole) -> Callable[[AuthContext], AuthContext]:
    """Builds a dependency that restricts access to the provided Clerk roles."""

    allowed = {_normalize_user_role(role) for role in allowed_roles}

    def dependency(auth_context: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if auth_context.role not in allowed:
            raise HTTPException(status_code=403, detail="You do not have permission to access this resource.")
        return auth_context

    return dependency


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

    public_metadata = _extract_public_metadata(principal)
    candidate = _extract_email_candidate(public_metadata.get("email"))
    if candidate is not None:
        return candidate

    return _extract_email_candidate(principal.get("email_addresses"))
