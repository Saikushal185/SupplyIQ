from __future__ import annotations

import json
import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend import dependencies, main
from backend.routers import analytics, forecast, inventory, pipeline


class _InMemoryCacheService:
    def __init__(self) -> None:
        self._data: dict[str, object] = {}

    def build_key(self, namespace: str, payload: dict[str, object]) -> str:
        return f"{namespace}:{json.dumps(payload, sort_keys=True, default=str)}"

    async def get_json(self, key: str) -> object | None:
        return self._data.get(key)

    async def set_json(self, key: str, value: object) -> None:
        self._data[key] = value


def _build_router_app(*, role: str = "admin") -> FastAPI:
    app = FastAPI()
    app.state.cache_service = _InMemoryCacheService()
    app.state.forecast_service = SimpleNamespace(generate_forecast=AsyncMock())
    app.include_router(analytics.router, prefix="/api/v1")
    app.include_router(forecast.router, prefix="/api/v1")
    app.include_router(inventory.router, prefix="/api/v1")
    app.include_router(pipeline.router, prefix="/api/v1")
    app.dependency_overrides[dependencies.get_db] = lambda: object()
    app.dependency_overrides[dependencies.get_auth_context] = lambda: dependencies.AuthContext(
        user_id="user_123",
        role=role,
        claims={"sub": "user_123"},
    )
    app.dependency_overrides[dependencies.get_current_user_email] = lambda: "planner@supplyiq.test"
    return app


class ApiContractTests(unittest.TestCase):
    def test_health_endpoint_returns_dependency_status_in_data_envelope(self) -> None:
        with (
            patch.object(main, "initialize_database", AsyncMock()),
            patch.object(main, "dispose_database_engine", AsyncMock()),
            patch.object(main, "CacheService"),
            patch.object(main, "ForecastService"),
            patch.object(main, "check_database_connection", AsyncMock(return_value=True)),
            patch.object(main, "check_redis_connection", AsyncMock(return_value=True)),
        ):
            client = TestClient(main.create_app())
            response = client.get("/api/v1/health")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"]["status"], "ok")
        self.assertTrue(body["data"]["db"])
        self.assertTrue(body["data"]["redis"])
        self.assertFalse(body["meta"]["cached"])
        self.assertIn("timestamp", body["meta"])

    def test_sales_endpoint_caches_responses_and_marks_cached_meta(self) -> None:
        app = _build_router_app(role="analyst")
        sales_rows = [
            {
                "region_id": str(uuid4()),
                "region_name": "West",
                "sale_date": "2026-03-01",
                "units_sold": 42,
                "revenue": 4200.0,
            }
        ]

        with patch("backend.services.db_service.get_sales_analytics", AsyncMock(return_value=sales_rows)) as sales_mock:
            client = TestClient(app)
            first = client.get("/api/v1/analytics/sales?start_date=2026-03-01&end_date=2026-03-05")
            second = client.get("/api/v1/analytics/sales?start_date=2026-03-01&end_date=2026-03-05")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["data"][0]["region_name"], "West")
        self.assertFalse(first.json()["meta"]["cached"])
        self.assertTrue(second.json()["meta"]["cached"])
        sales_mock.assert_awaited_once()

    def test_analytics_filters_endpoint_returns_cached_filter_options(self) -> None:
        app = _build_router_app(role="viewer")
        filter_options = {
            "regions": [
                {
                    "region_id": str(uuid4()),
                    "region_name": "Dallas",
                }
            ],
            "products": [
                {
                    "product_id": str(uuid4()),
                    "product_name": "Handheld Scanner",
                    "sku": "HS-100",
                    "category": "Scanning",
                }
            ],
            "categories": ["Scanning"],
        }

        with patch(
            "backend.routers.analytics.get_analytics_filter_options",
            AsyncMock(return_value=filter_options),
        ) as filters_mock:
            client = TestClient(app)
            first = client.get("/api/v1/analytics/filters")
            second = client.get("/api/v1/analytics/filters")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["data"]["categories"], ["Scanning"])
        self.assertFalse(first.json()["meta"]["cached"])
        self.assertTrue(second.json()["meta"]["cached"])
        filters_mock.assert_awaited_once()

    def test_product_sales_and_forecast_run_endpoints_return_enveloped_payloads(self) -> None:
        app = _build_router_app(role="analyst")
        product_sales_rows = [
            {
                "product_id": str(uuid4()),
                "product_name": "Handheld Scanner",
                "sku": "HS-100",
                "category": "Scanning",
                "units_sold": 128,
                "revenue": 12800.0,
            }
        ]

        with (
            patch("backend.services.db_service.get_product_sales_summary", AsyncMock(return_value=product_sales_rows)),
            patch("backend.services.db_service.count_forecast_runs", AsyncMock(return_value=4)),
        ):
            client = TestClient(app)
            product_sales_response = client.get(
                "/api/v1/analytics/product-sales?start_date=2026-03-01&end_date=2026-03-31&category=Scanning"
            )
            forecast_runs_response = client.get("/api/v1/analytics/forecast-runs?run_date=2026-03-28")

        self.assertEqual(product_sales_response.status_code, 200)
        self.assertEqual(forecast_runs_response.status_code, 200)
        self.assertEqual(product_sales_response.json()["data"][0]["units_sold"], 128)
        self.assertEqual(product_sales_response.json()["data"][0]["category"], "Scanning")
        self.assertEqual(forecast_runs_response.json()["data"]["count"], 4)

    def test_forecast_generation_forbids_viewers(self) -> None:
        app = _build_router_app(role="viewer")
        app.state.forecast_service.generate_forecast = AsyncMock(
            return_value={
                "forecast_id": str(uuid4()),
                "product_id": str(uuid4()),
                "region_id": str(uuid4()),
                "product_name": "Scanner",
                "region_name": "Dallas",
                "run_at": datetime.now(timezone.utc).isoformat(),
                "forecast_json": {
                    "horizon_days": 7,
                    "predictions": [],
                    "summary": {
                        "total_units": 0,
                        "avg_daily_units": 0.0,
                        "stockout_risk_pct": 0.0,
                        "recommended_reorder_units": 0,
                    },
                },
                "shap_json": {"method": "shap_tree_explainer", "top_features": []},
            }
        )
        client = TestClient(app)

        response = client.post(
            "/api/v1/forecast/generate",
            json={
                "product_id": str(uuid4()),
                "region_id": str(uuid4()),
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_inventory_summary_returns_standard_response_envelope(self) -> None:
        app = _build_router_app(role="viewer")
        summary_rows = [
            {
                "product_id": str(uuid4()),
                "product_name": "Handheld Scanner",
                "sku": "HS-100",
                "region_id": str(uuid4()),
                "region_name": "Dallas",
                "quantity": 18,
                "snapshot_date": date(2026, 3, 10).isoformat(),
                "reorder_point": 25,
                "risk_level": "high",
            }
        ]

        with patch("backend.services.db_service.get_inventory_summary", AsyncMock(return_value=summary_rows)):
            client = TestClient(app)
            response = client.get("/api/v1/inventory/summary")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"][0]["sku"], "HS-100")
        self.assertFalse(response.json()["meta"]["cached"])

    def test_inventory_history_returns_enveloped_snapshot_rows(self) -> None:
        app = _build_router_app(role="viewer")
        product_id = uuid4()
        history_rows = [
            {
                "product_id": str(product_id),
                "product_name": "Handheld Scanner",
                "region_id": str(uuid4()),
                "region_name": "Dallas",
                "snapshot_date": "2026-03-10",
                "quantity": 18,
            },
            {
                "product_id": str(product_id),
                "product_name": "Handheld Scanner",
                "region_id": str(uuid4()),
                "region_name": "Atlanta",
                "snapshot_date": "2026-03-11",
                "quantity": 14,
            },
        ]

        with patch("backend.services.db_service.get_inventory_history", AsyncMock(return_value=history_rows)):
            client = TestClient(app)
            response = client.get(f"/api/v1/inventory/{product_id}/history")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]), 2)
        self.assertFalse(response.json()["meta"]["cached"])

    def test_remaining_analytics_endpoints_return_enveloped_payloads(self) -> None:
        app = _build_router_app(role="analyst")
        turnover_rows = [
            {
                "product_id": str(uuid4()),
                "product_name": "Handheld Scanner",
                "sku": "HS-100",
                "cost_of_goods": 4200.0,
                "average_inventory_value": 1400.0,
                "turnover_ratio": 3.0,
            }
        ]
        reliability_rows = [
            {
                "supplier_name": "Northwind",
                "shipment_count": 10,
                "delivered_count": 8,
                "delayed_count": 1,
                "in_transit_count": 1,
                "on_time_rate_pct": 87.5,
            }
        ]
        growth_rows = [
            {
                "region_id": str(uuid4()),
                "region_name": "Dallas",
                "current_month": "2026-03-01",
                "previous_month": "2026-02-01",
                "revenue": 12500.0,
                "previous_revenue": 10000.0,
                "growth_pct": 25.0,
            }
        ]

        with (
            patch("backend.services.db_service.get_inventory_turnover", AsyncMock(return_value=turnover_rows)),
            patch("backend.services.db_service.get_supplier_reliability", AsyncMock(return_value=reliability_rows)),
            patch("backend.routers.analytics.get_regional_growth", AsyncMock(return_value=growth_rows)),
        ):
            client = TestClient(app)
            turnover_response = client.get("/api/v1/analytics/turnover")
            reliability_response = client.get("/api/v1/analytics/supplier-reliability")
            growth_response = client.get("/api/v1/analytics/regional-growth")

        self.assertEqual(turnover_response.status_code, 200)
        self.assertEqual(reliability_response.status_code, 200)
        self.assertEqual(growth_response.status_code, 200)
        self.assertEqual(turnover_response.json()["data"][0]["turnover_ratio"], 3.0)
        self.assertEqual(reliability_response.json()["data"][0]["supplier_name"], "Northwind")
        self.assertEqual(growth_response.json()["data"][0]["growth_pct"], 25.0)

    def test_forecast_read_endpoints_return_enveloped_data_for_analysts(self) -> None:
        app = _build_router_app(role="analyst")
        product_id = uuid4()
        region_id = uuid4()
        forecast_record = {
            "forecast_id": str(uuid4()),
            "product_id": str(product_id),
            "region_id": str(region_id),
            "product_name": "Scanner",
            "region_name": "Dallas",
            "run_at": datetime.now(timezone.utc).isoformat(),
            "forecast_json": {
                "horizon_days": 7,
                "predictions": [],
                "summary": {
                    "total_units": 70,
                    "avg_daily_units": 10.0,
                    "stockout_risk_pct": 20.0,
                    "recommended_reorder_units": 18,
                },
            },
            "shap_json": {"method": "shap_tree_explainer", "top_features": []},
        }

        with (
            patch("backend.services.db_service.get_latest_forecast", AsyncMock(return_value=forecast_record)),
            patch("backend.services.db_service.get_forecast_history", AsyncMock(return_value=[forecast_record])),
        ):
            client = TestClient(app)
            latest_response = client.get(f"/api/v1/forecast/latest/{product_id}/{region_id}")
            history_response = client.get(f"/api/v1/forecast/history/{product_id}")

        self.assertEqual(latest_response.status_code, 200)
        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(latest_response.json()["data"]["product_name"], "Scanner")
        self.assertEqual(len(history_response.json()["data"]), 1)

    def test_pipeline_status_is_admin_only(self) -> None:
        viewer_client = TestClient(_build_router_app(role="viewer"))
        viewer_response = viewer_client.get("/api/v1/pipeline/status")

        self.assertEqual(viewer_response.status_code, 403)

        admin_app = _build_router_app(role="admin")
        with patch(
            "backend.routers.pipeline.get_latest_pipeline_status",
            AsyncMock(
                return_value={
                    "flow_run_id": "flow-run-1",
                    "flow_name": "ingestion",
                    "deployment_id": "deployment-1",
                    "deployment_name": "ingestion",
                    "state_type": "COMPLETED",
                    "state_name": "Completed",
                    "start_time": "2026-03-26T06:00:00Z",
                    "end_time": "2026-03-26T06:05:00Z",
                }
            ),
        ):
            admin_client = TestClient(admin_app)
            admin_response = admin_client.get("/api/v1/pipeline/status")

        self.assertEqual(admin_response.status_code, 200)
        self.assertEqual(admin_response.json()["data"]["state_name"], "Completed")


if __name__ == "__main__":
    unittest.main()
