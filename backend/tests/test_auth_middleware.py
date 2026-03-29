from __future__ import annotations

import unittest

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from backend.middleware.auth import ClerkAuthMiddleware


class _Verifier:
    async def verify_token(self, token: str) -> dict[str, object]:
        return {
            "sub": "user_123",
            "public_metadata": {
                "role": "admin",
            },
        }


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        ClerkAuthMiddleware,
        enabled=True,
        verifier=_Verifier(),
        public_paths={"/health"},
    )

    @app.get("/protected")
    async def protected(request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "user_id": getattr(request.state, "user_id", None),
                "role": getattr(request.state, "role", None),
            }
        )

    return app


class ClerkAuthMiddlewareTests(unittest.TestCase):
    def test_authenticated_request_exposes_user_id_and_role_on_request_state(self) -> None:
        client = TestClient(_build_app())

        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer token"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "user_id": "user_123",
                "role": "admin",
            },
        )

    def test_missing_bearer_token_is_rejected(self) -> None:
        client = TestClient(_build_app())

        response = client.get("/protected")

        self.assertEqual(response.status_code, 401)
        self.assertIn("detail", response.json())


if __name__ == "__main__":
    unittest.main()
