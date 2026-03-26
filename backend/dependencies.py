"""FastAPI dependencies for backend services."""

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.schemas import UserRole
from backend.services.cache_service import CacheService
from backend.services.db_service import get_db_session
from backend.services.forecast_service import ForecastService
from backend.settings import Settings, get_settings

VALID_USER_ROLES: set[str] = {"admin", "analyst", "viewer"}


@dataclass(slots=True)
class AuthContext:
    """Represents the authenticated Clerk principal used for request authorization."""

    user_id: str
    role: UserRole
    claims: dict[str, object]


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


def _extract_role_candidate(value: object) -> str | None:
    """Returns the first string role candidate nested in Clerk metadata payloads."""

    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized or None
    if isinstance(value, dict):
        for key in ("role",):
            candidate = _extract_role_candidate(value.get(key))
            if candidate is not None:
                return candidate
    return None


def normalize_user_role(value: object) -> UserRole:
    """Normalizes arbitrary Clerk metadata into a least-privilege application role."""

    candidate = _extract_role_candidate(value)
    if candidate in VALID_USER_ROLES:
        return candidate  # type: ignore[return-value]
    return "viewer"


def build_auth_context(principal: object) -> AuthContext:
    """Builds the typed auth context from Clerk JWT claims."""

    if not isinstance(principal, dict):
        raise HTTPException(status_code=401, detail="Missing authenticated principal.")

    user_id = principal.get("sub") or principal.get("user_id")
    if not isinstance(user_id, str) or not user_id.strip():
        raise HTTPException(status_code=401, detail="Authenticated principal is missing a Clerk user id.")

    role = normalize_user_role(
        principal.get("public_metadata")
        or principal.get("publicMetadata")
        or principal.get("metadata")
    )
    return AuthContext(user_id=user_id, role=role, claims=principal)


def get_auth_context(request: Request) -> AuthContext:
    """Returns the typed authentication context extracted from Clerk JWT claims."""

    settings = get_settings()
    if not settings.auth_enabled:
        return AuthContext(user_id="local-dev-user", role="admin", claims={})

    principal = getattr(request.state, "principal", None)
    return build_auth_context(principal)


def require_roles(*roles: UserRole):
    """Creates a dependency that rejects authenticated users missing one of the required roles."""

    allowed_roles = set(roles)

    def dependency(auth_context: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if auth_context.role not in allowed_roles:
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

    return _extract_email_candidate(principal.get("email_addresses"))
