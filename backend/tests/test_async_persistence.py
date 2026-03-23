"""Regression tests for async backend persistence boundaries."""

from __future__ import annotations

import inspect
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from backend.models.schemas import AnalyticsQuery, InventoryPositionItem, KPI
from backend.routers import analytics
from backend.services import db_service
from backend.services.cache_service import CacheService


class DatabaseUrlTests(unittest.TestCase):
    """Verifies database URL normalization for async SQLAlchemy."""

    def test_build_async_database_url_rewrites_psycopg_driver(self) -> None:
        """Converts sync psycopg SQLAlchemy URLs into asyncpg URLs."""

        self.assertEqual(
            db_service.build_async_database_url(
                "postgresql+psycopg://supplyiq:secret@postgres:5432/supplyiq",
            ),
            "postgresql+asyncpg://supplyiq:secret@postgres:5432/supplyiq",
        )

    def test_db_session_dependency_is_async_generator(self) -> None:
        """Ensures FastAPI DB dependency yields async sessions."""

        self.assertTrue(inspect.isasyncgenfunction(db_service.get_db_session))


class CacheServiceAsyncTests(unittest.IsolatedAsyncioTestCase):
    """Validates Redis access uses awaitable client calls."""

    async def test_cache_service_supports_async_redis_client(self) -> None:
        """Reads and writes cached JSON through an async Redis client."""

        client = MagicMock()
        client.get = AsyncMock(return_value='{"status":"ok"}')
        client.setex = AsyncMock()

        service = CacheService(client=client, ttl_seconds=45)

        cached = await service.get_json("analytics:key")
        await service.set_json("analytics:key", {"status": "ok"})

        self.assertEqual(cached, {"status": "ok"})
        client.get.assert_awaited_once_with("analytics:key")
        client.setex.assert_awaited_once()


class AnalyticsRouteAsyncTests(unittest.IsolatedAsyncioTestCase):
    """Confirms routes work with async DB and cache services."""

    async def test_overview_route_awaits_async_dependencies(self) -> None:
        """Builds the analytics overview via async DB and Redis helpers."""

        query = AnalyticsQuery(region_code="US-SOUTH", lookback_days=30)
        cache_service = MagicMock()
        cache_service.build_key.return_value = "analytics:overview:test"
        cache_service.get_json = AsyncMock(return_value=None)
        cache_service.set_json = AsyncMock()

        positions = [
            InventoryPositionItem(
                product_id=uuid4(),
                product_name="Wireless Scanner",
                sku="SKU-1001",
                region_id=uuid4(),
                region_name="Dallas Distribution Center",
                quantity_on_hand=920,
                quantity_reserved=180,
                inbound_units=240,
                reorder_point=640,
                days_of_cover=15.9,
                risk_level="medium",
            )
        ]
        kpis = [
            KPI(
                label="Inventory Units",
                value=920,
                change_note="Current on-hand inventory across active positions.",
            )
        ]

        with (
            patch("backend.routers.analytics.db_service.build_analytics_kpis", new=AsyncMock(return_value=kpis)),
            patch("backend.routers.analytics.db_service.list_inventory_positions", new=AsyncMock(return_value=positions)),
        ):
            response = await analytics.get_overview(query, object(), cache_service)

        self.assertEqual(response.region_code, "US-SOUTH")
        self.assertEqual(response.kpis[0].label, "Inventory Units")
        cache_service.get_json.assert_awaited_once_with("analytics:overview:test")
        cache_service.set_json.assert_awaited_once()
