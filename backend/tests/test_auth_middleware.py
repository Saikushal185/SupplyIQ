"""Tests for Clerk-backed route protection middleware."""

from __future__ import annotations

import unittest

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.testclient import TestClient

from backend.middleware.auth import ClerkAuthMiddleware


class _Verifier:
    """Simple verifier stub for middleware tests."""

    def __init__(self) -> None:
        self.tokens: list[str] = []

    async def verify_token(self, token: str) -> dict[str, str]:
        """Records the token and returns a fake subject."""

        self.tokens.append(token)
        return {"sub": "user_123"}


class ClerkAuthMiddlewareTests(unittest.TestCase):
    """Validates public-route bypass and protected-route enforcement."""

    def test_public_paths_bypass_authentication(self) -> None:
        """Allows the health endpoint through even when auth is enabled."""

        app = FastAPI()
        app.add_middleware(
            ClerkAuthMiddleware,
            enabled=True,
            verifier=_Verifier(),
            public_paths={"/api/v1/health"},
        )

        @app.get("/api/v1/health")
        async def health() -> JSONResponse:
            return JSONResponse({"status": "ok"})

        with TestClient(app) as client:
            response = client.get("/api/v1/health")

        self.assertEqual(response.status_code, 200)

    def test_missing_bearer_token_rejects_protected_routes(self) -> None:
        """Rejects protected routes when auth is enabled and no bearer token is provided."""

        app = FastAPI()
        app.add_middleware(
            ClerkAuthMiddleware,
            enabled=True,
            verifier=_Verifier(),
            public_paths={"/api/v1/health"},
        )

        @app.get("/api/v1/secure")
        async def secure_endpoint(request: Request) -> JSONResponse:
            return JSONResponse({"principal": getattr(request.state, "principal", None)})

        with TestClient(app) as client:
            response = client.get("/api/v1/secure")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Missing bearer token.")
