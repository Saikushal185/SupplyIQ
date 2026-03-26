"""Clerk-backed authentication middleware for protected API routes."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx
import jwt
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.dependencies import build_auth_context


class AuthError(Exception):
    """Represents a request authentication failure."""


CLERK_JWKS_SUFFIX = "/.well-known/jwks.json"


def resolve_clerk_jwks_url(jwks_url: str | None) -> str | None:
    """Normalizes a Clerk frontend API URL into the latest JWKS endpoint format."""

    configured_url = jwks_url or os.getenv("CLERK_JWKS_URL")
    if not configured_url:
        return None

    normalized_url = configured_url.strip().rstrip("/")
    if normalized_url.endswith(CLERK_JWKS_SUFFIX):
        return normalized_url
    return f"{normalized_url}{CLERK_JWKS_SUFFIX}"


@dataclass(slots=True)
class ClerkTokenVerifier:
    """Validates Clerk session tokens against the configured JWKS endpoint."""

    jwks_url: str | None = None
    issuer: str | None = None
    audience: str | None = None
    cache_ttl_seconds: int = 300

    def __post_init__(self) -> None:
        self.jwks_url = resolve_clerk_jwks_url(self.jwks_url)
        self._cached_jwks: dict[str, Any] | None = None
        self._cached_at: float = 0.0

    async def verify_token(self, token: str) -> dict[str, Any]:
        """Fetches the active signing keys and validates a bearer token."""

        try:
            header = jwt.get_unverified_header(token)
        except jwt.InvalidTokenError as exc:
            raise AuthError("Invalid bearer token.") from exc

        kid = header.get("kid")
        if not isinstance(kid, str) or not kid:
            raise AuthError("Bearer token is missing a signing key identifier.")

        jwks = await self._get_jwks()
        public_key = self._resolve_public_key(jwks, kid)

        try:
            return jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"verify_aud": bool(self.audience)},
            )
        except jwt.InvalidTokenError as exc:
            raise AuthError("Invalid or expired bearer token.") from exc

    async def _get_jwks(self) -> dict[str, Any]:
        """Returns cached JWKS data or refreshes it from Clerk."""

        if not self.jwks_url:
            raise AuthError("Clerk JWKS URL is not configured.")

        now = time.time()
        if self._cached_jwks is not None and now - self._cached_at < self.cache_ttl_seconds:
            return self._cached_jwks

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(self.jwks_url)
            response.raise_for_status()
            self._cached_jwks = response.json()
            self._cached_at = now
            return self._cached_jwks

    def _resolve_public_key(self, jwks: dict[str, Any], kid: str) -> Any:
        """Resolves the matching RSA public key from the active JWKS payload."""

        keys = jwks.get("keys", [])
        matching_key = next((item for item in keys if item.get("kid") == kid), None)
        if matching_key is None:
            raise AuthError("Unable to find a signing key for the provided bearer token.")
        return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(matching_key))


class ClerkAuthMiddleware(BaseHTTPMiddleware):
    """Protects configured routes using Clerk-issued bearer tokens."""

    def __init__(
        self,
        app: Any,
        *,
        enabled: bool,
        verifier: ClerkTokenVerifier | Any | None,
        public_paths: set[str],
    ) -> None:
        super().__init__(app)
        self._enabled = enabled
        self._verifier = verifier
        self._public_paths = {path.rstrip("/") or "/" for path in public_paths}

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Skips public routes and validates bearer tokens for protected ones."""

        if not self._enabled or request.method == "OPTIONS" or self._is_public_path(request.url.path):
            return await call_next(request)

        if self._verifier is None:
            return JSONResponse(status_code=503, content={"detail": "Authentication is enabled but not configured."})

        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing bearer token."})

        token = authorization.removeprefix("Bearer ").strip()
        if not token:
            return JSONResponse(status_code=401, content={"detail": "Missing bearer token."})

        try:
            principal = await self._verifier.verify_token(token)
        except AuthError as exc:
            return JSONResponse(status_code=401, content={"detail": str(exc)})
        except httpx.HTTPError:
            return JSONResponse(status_code=503, content={"detail": "Unable to validate bearer token right now."})

        request.state.principal = principal
        try:
            auth_context = build_auth_context(principal)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        request.state.user_id = auth_context.user_id
        request.state.role = auth_context.role
        return await call_next(request)

    def _is_public_path(self, path: str) -> bool:
        """Returns whether the request path is excluded from auth protection."""

        normalized_path = path.rstrip("/") or "/"
        return normalized_path in self._public_paths
