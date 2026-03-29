from __future__ import annotations

import unittest
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from backend.ml import predict
from backend.ml import train


def _build_observations() -> list[predict.SalesObservation]:
    base_date = date(2026, 3, 1)
    units = [10, 12, 14, 16, 18, 20, 22, 24]
    return [
        predict.SalesObservation(
            sale_date=base_date + timedelta(days=index),
            units_sold=units_sold,
            weather_temp=70.0 + index,
            traffic_index=0.4 + (index * 0.01),
        )
        for index, units_sold in enumerate(units)
    ]


class ForecastPipelineTests(unittest.IsolatedAsyncioTestCase):
    def test_build_prophet_artifact_path_scopes_to_product_region_pair(self) -> None:
        product_id = uuid4()
        region_id = uuid4()

        artifact_path = predict.build_prophet_artifact_path(product_id, region_id)

        self.assertEqual(
            artifact_path.name,
            f"prophet_{product_id}_{region_id}.joblib",
        )

    def test_load_prophet_model_for_scope_raises_404_when_pair_artifact_missing(self) -> None:
        product_id = uuid4()
        region_id = uuid4()
        missing_artifact_dir = Path("backend") / "tests" / f"missing_artifacts_{uuid4()}"

        with patch.object(predict, "ARTIFACT_DIR", missing_artifact_dir):
            with self.assertRaises(predict.HTTPException) as exc_info:
                predict.load_prophet_model_for_scope(product_id, region_id)

        self.assertEqual(exc_info.exception.status_code, 404)
        self.assertEqual(
            exc_info.exception.detail,
            "No trained model found for this product-region combination. Run train.py first.",
        )

    def test_build_residual_training_rows_keeps_each_scope_isolated(self) -> None:
        scope_a = [
            predict.SalesObservation(
                sale_date=date(2026, 1, 1) + timedelta(days=offset),
                units_sold=value,
                weather_temp=70.0,
                traffic_index=0.4,
                product_id="product-a",
                region_id="region-a",
            )
            for offset, value in enumerate((10, 20, 30))
        ]
        scope_b = [
            predict.SalesObservation(
                sale_date=date(2026, 1, 1) + timedelta(days=offset),
                units_sold=value,
                weather_temp=65.0,
                traffic_index=0.3,
                product_id="product-b",
                region_id="region-b",
            )
            for offset, value in enumerate((100, 110, 120))
        ]

        feature_rows = train.build_residual_training_rows([*scope_a, *scope_b])

        self.assertEqual(len(feature_rows), 6)
        self.assertEqual(feature_rows[0]["lag_1"], 0.0)
        self.assertEqual(feature_rows[3]["lag_1"], 0.0)
        self.assertEqual(feature_rows[2]["lag_1"], 20.0)
        self.assertEqual(feature_rows[5]["lag_1"], 110.0)

    def test_engineer_history_features_derives_calendar_rollups_and_lags(self) -> None:
        engineered_rows = predict.engineer_history_features(_build_observations())

        latest_row = engineered_rows[-1]

        self.assertEqual(latest_row["ds"], date(2026, 3, 8))
        self.assertEqual(latest_row["y"], 24.0)
        self.assertEqual(latest_row["day_of_week"], 6)
        self.assertTrue(latest_row["is_weekend"])
        self.assertEqual(latest_row["month"], 3)
        self.assertAlmostEqual(latest_row["rolling_7d_avg"], 16.0)
        self.assertAlmostEqual(latest_row["lag_1"], 22.0)
        self.assertAlmostEqual(latest_row["lag_7"], 10.0)

    def test_build_future_feature_rows_rolls_predictions_forward(self) -> None:
        history_rows = predict.engineer_history_features(_build_observations())
        future_dates = [date(2026, 3, 9), date(2026, 3, 10)]

        future_rows = predict.build_future_feature_rows(
            history_rows,
            future_dates,
            [30.0, 40.0],
        )

        self.assertEqual(len(future_rows), 2)
        self.assertAlmostEqual(future_rows[0]["lag_1"], 24.0)
        self.assertAlmostEqual(future_rows[0]["lag_7"], 12.0)
        self.assertAlmostEqual(future_rows[0]["rolling_7d_avg"], 18.0)
        self.assertAlmostEqual(future_rows[1]["lag_1"], 30.0)
        self.assertAlmostEqual(future_rows[1]["lag_7"], 14.0)
        self.assertAlmostEqual(future_rows[1]["rolling_7d_avg"], 144.0 / 7.0)

    def test_summarize_feature_impacts_returns_top_five_with_direction_and_value(self) -> None:
        feature_rows = [
            {
                "weather_temp": 74.0,
                "traffic_index": 0.52,
                "day_of_week": 1,
                "is_weekend": 0,
                "month": 3,
                "rolling_7d_avg": 19.0,
                "lag_1": 22.0,
                "lag_7": 12.0,
            },
            {
                "weather_temp": 76.0,
                "traffic_index": 0.57,
                "day_of_week": 2,
                "is_weekend": 0,
                "month": 3,
                "rolling_7d_avg": 20.5,
                "lag_1": 30.0,
                "lag_7": 14.0,
            },
        ]
        shap_values = [
            [0.4, -0.2, 0.1, 0.0, 0.05, 0.3, 0.9, -0.1],
            [0.3, -0.25, 0.12, 0.02, 0.04, 0.28, 0.75, -0.08],
        ]

        top_features = predict.summarize_feature_impacts(feature_rows, shap_values, top_n=5)

        self.assertEqual(len(top_features), 5)
        self.assertEqual(top_features[0]["feature"], "lag_1")
        self.assertEqual(top_features[0]["direction"], "up")
        self.assertAlmostEqual(top_features[0]["value"], 26.0)
        self.assertGreater(top_features[0]["contribution"], top_features[-1]["contribution"])

    def test_detect_stockout_risk_returns_first_exhaustion_day(self) -> None:
        forecast_days = [
            {"date": "2026-03-09", "predicted_units": 40.0},
            {"date": "2026-03-10", "predicted_units": 55.0},
            {"date": "2026-03-11", "predicted_units": 60.0},
        ]

        alert = predict.detect_stockout_risk(
            current_inventory=95,
            reorder_point=30,
            forecast_days=forecast_days,
        )

        self.assertIsNotNone(alert)
        self.assertEqual(alert["stockout_date"], "2026-03-10")
        self.assertEqual(alert["current_stock_level"], 95)
        self.assertEqual(alert["remaining_inventory"], 55)

    async def test_generate_forecast_combines_baseline_residuals_persists_and_sends_email(self) -> None:
        product_id = uuid4()
        region_id = uuid4()
        base_date = date(2026, 3, 9)
        history_rows = predict.engineer_history_features(_build_observations())
        future_rows = predict.build_future_feature_rows(
            history_rows,
            [base_date + timedelta(days=offset) for offset in range(7)],
            [28.0, 29.0, 30.0, 31.0, 29.0, 28.0, 27.0],
        )
        prophet_forecast = [
            {
                "date": (base_date + timedelta(days=offset)).isoformat(),
                "yhat": value,
                "yhat_lower": value - 3,
                "yhat_upper": value + 4,
            }
            for offset, value in enumerate((28.0, 29.0, 30.0, 31.0, 29.0, 28.0, 27.0))
        ]
        inventory_context = SimpleNamespace(
            quantity=25,
            product=SimpleNamespace(id=product_id, name="Wireless Scanner", reorder_point=20),
            region=SimpleNamespace(id=region_id, name="Dallas"),
        )
        persisted_payload = {
            "forecast_id": uuid4(),
            "product_id": product_id,
            "region_id": region_id,
            "product_name": "Wireless Scanner",
            "region_name": "Dallas",
            "forecast_json": {"predictions": []},
            "shap_json": {"top_features": []},
        }

        with (
            patch.object(predict, "_load_recent_sales_history", AsyncMock(return_value=_build_observations())),
            patch.object(predict, "_load_inventory_context", AsyncMock(return_value=inventory_context)),
            patch.object(predict, "load_prophet_model_for_scope", return_value=object()) as load_prophet_mock,
            patch.object(predict, "_forecast_prophet_baseline", return_value=prophet_forecast),
            patch.object(predict, "_predict_residual_corrections", return_value=[2.0] * 7),
            patch.object(
                predict,
                "_compute_shap_values",
                return_value=[[0.1, 0.05, 0.02, 0.0, 0.01, 0.03, 0.2, -0.04] for _ in range(7)],
            ),
            patch.object(predict, "build_future_feature_rows", return_value=future_rows),
            patch.object(predict, "_save_forecast_run", AsyncMock(return_value=persisted_payload)) as save_mock,
        ):
            email_sender = AsyncMock()
            result = await predict.generate_forecast(
                product_id,
                region_id,
                db_session=object(),
                user_email="planner@supplyiq.test",
                email_sender=email_sender,
            )

        self.assertEqual(result, persisted_payload)
        load_prophet_mock.assert_called_once_with(product_id, region_id)
        saved_forecast = save_mock.await_args.kwargs["forecast_json"]
        self.assertEqual(len(saved_forecast["predictions"]), 7)
        self.assertEqual(saved_forecast["predictions"][0]["predicted_units"], 30)
        self.assertEqual(saved_forecast["predictions"][0]["units"], 30)
        saved_shap = save_mock.await_args.kwargs["shap_json"]
        self.assertEqual(len(saved_shap["top_features"]), 5)
        email_sender.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
