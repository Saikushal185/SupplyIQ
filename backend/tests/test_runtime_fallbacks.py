from __future__ import annotations

import json
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from backend import dependencies
from backend.services import db_service
from backend.services.cache_service import CacheService


class _ExplodingCacheClient:
    async def get(self, key: str):
        raise RuntimeError(f"boom:{key}")

    async def setex(self, key: str, ttl: int, value: str):
        raise RuntimeError(f"boom:{key}:{ttl}:{value}")

    async def ping(self):
        raise RuntimeError("boom:ping")

    async def aclose(self):
        return None


class RuntimeFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_cache_service_falls_back_when_redis_is_unreachable(self) -> None:
        cache_service = CacheService(client=_ExplodingCacheClient(), ttl_seconds=30)

        cached = await cache_service.get_json("analytics:test")
        await cache_service.set_json("analytics:test", {"ok": True})
        ping_ok = await cache_service.ping()

        self.assertIsNone(cached)
        self.assertFalse(ping_ok)

    def test_get_auth_context_returns_demo_admin_when_auth_is_disabled(self) -> None:
        request = SimpleNamespace(state=SimpleNamespace())

        with patch.object(dependencies, "get_settings", return_value=SimpleNamespace(auth_enabled=False)):
            auth_context = dependencies.get_auth_context(request)

        self.assertEqual(auth_context.user_id, "demo-operator")
        self.assertEqual(auth_context.role, "admin")
        self.assertEqual(auth_context.claims, {"sub": "demo-operator", "role": "admin", "mode": "demo"})

    def test_utc_day_bounds_are_timezone_normalized_for_timestamp_columns(self) -> None:
        start_dt, end_dt = db_service.utc_day_bounds(date(2026, 3, 31))

        self.assertIsNone(start_dt.tzinfo)
        self.assertIsNone(end_dt.tzinfo)
        self.assertEqual(start_dt.isoformat(), "2026-03-31T00:00:00")
        self.assertEqual(end_dt.isoformat(), "2026-04-01T00:00:00")


if __name__ == "__main__":
    unittest.main()
