"""Forecast model loading and inference service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import joblib
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ml.predict import build_feature_vector, run_inference
from backend.models.db_models import DailySale, SupplierShipment
from backend.models.schemas import ForecastGenerateRequest, ForecastRecordResponse
from backend.services import db_service


@dataclass(slots=True)
class ForecastArtifact:
    """Represents a loaded serialized forecast model artifact."""

    model: Any
    feature_names: list[str]
    version: str


@dataclass(slots=True)
class SalesSignals:
    """Represents recent sales-derived forecasting signals."""

    avg_units_sold_7d: float
    avg_units_sold_30d: float
    total_revenue_30d: float
    avg_weather_temp_30d: float
    avg_traffic_index_30d: float


@dataclass(slots=True)
class ShipmentSignals:
    """Represents supplier-shipment-derived forecasting signals."""

    incoming_shipment_units_7d: float
    delayed_shipment_units: float


class ForecastService:
    """Loads the forecast artifact once and serves inference requests."""

    def __init__(self, artifact_path: Path) -> None:
        self._artifact_path = artifact_path
        self._artifact = self._load_artifact()

    def _load_artifact(self) -> ForecastArtifact:
        """Loads and validates the serialized joblib artifact."""

        if not self._artifact_path.exists():
            raise FileNotFoundError(f"Forecast model artifact not found: {self._artifact_path}")
        raw_artifact = joblib.load(self._artifact_path)
        if not isinstance(raw_artifact, dict) or "model" not in raw_artifact:
            raise ValueError("Forecast model artifact is invalid or missing the model object.")
        return ForecastArtifact(
            model=raw_artifact["model"],
            feature_names=list(raw_artifact.get("feature_names", [])),
            version=str(raw_artifact.get("version", "unknown")),
        )

    async def _load_sales_signals(
        self,
        session: AsyncSession,
        *,
        product_id: Any,
        region_id: Any,
    ) -> SalesSignals:
        """Aggregates recent daily sales into forecast features."""

        today = date.today()
        last_7_days = today - timedelta(days=7)
        last_30_days = today - timedelta(days=30)
        statement = (
            select(
                func.coalesce(func.avg(case((DailySale.sale_date >= last_7_days, DailySale.units_sold), else_=None)), 0),
                func.coalesce(func.avg(DailySale.units_sold), 0),
                func.coalesce(func.sum(DailySale.revenue), 0),
                func.coalesce(func.avg(DailySale.weather_temp), 0),
                func.coalesce(func.avg(DailySale.traffic_index), 0),
            )
            .where(
                DailySale.product_id == product_id,
                DailySale.region_id == region_id,
                DailySale.sale_date >= last_30_days,
            )
        )
        avg_units_sold_7d, avg_units_sold_30d, total_revenue_30d, avg_weather_temp_30d, avg_traffic_index_30d = (
            await session.execute(statement)
        ).one()
        return SalesSignals(
            avg_units_sold_7d=float(avg_units_sold_7d or 0),
            avg_units_sold_30d=float(avg_units_sold_30d or 0),
            total_revenue_30d=float(total_revenue_30d or 0),
            avg_weather_temp_30d=float(avg_weather_temp_30d or 0),
            avg_traffic_index_30d=float(avg_traffic_index_30d or 0),
        )

    async def _load_shipment_signals(
        self,
        session: AsyncSession,
        *,
        product_id: Any,
    ) -> ShipmentSignals:
        """Aggregates supplier shipments into forecast features."""

        today = date.today()
        next_7_days = today + timedelta(days=7)
        statement = select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                SupplierShipment.expected_date.is_not(None),
                                SupplierShipment.expected_date >= today,
                                SupplierShipment.expected_date <= next_7_days,
                                SupplierShipment.status.in_(("in_transit", "delayed")),
                            ),
                            SupplierShipment.quantity,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(case((SupplierShipment.status == "delayed", SupplierShipment.quantity), else_=0)),
                0,
            ),
        ).where(SupplierShipment.product_id == product_id)
        incoming_shipment_units_7d, delayed_shipment_units = (await session.execute(statement)).one()
        return ShipmentSignals(
            incoming_shipment_units_7d=float(incoming_shipment_units_7d or 0),
            delayed_shipment_units=float(delayed_shipment_units or 0),
        )

    async def generate_forecast(
        self,
        session: AsyncSession,
        request: ForecastGenerateRequest,
    ) -> ForecastRecordResponse:
        """Generates and persists a forecast for a single product-region pair."""

        snapshot = await db_service.get_inventory_context(
            session,
            product_id=request.product_id,
            region_id=request.region_id,
        )
        sales_signals = await self._load_sales_signals(
            session,
            product_id=request.product_id,
            region_id=request.region_id,
        )
        shipment_signals = await self._load_shipment_signals(
            session,
            product_id=request.product_id,
        )

        feature_vector = build_feature_vector(
            current_quantity=snapshot.quantity,
            reorder_point=snapshot.product.reorder_point or 0,
            unit_cost=float(snapshot.product.unit_cost or 0),
            avg_units_sold_7d=sales_signals.avg_units_sold_7d,
            avg_units_sold_30d=sales_signals.avg_units_sold_30d,
            total_revenue_30d=sales_signals.total_revenue_30d,
            avg_weather_temp_30d=sales_signals.avg_weather_temp_30d,
            avg_traffic_index_30d=sales_signals.avg_traffic_index_30d,
            incoming_shipment_units_7d=shipment_signals.incoming_shipment_units_7d,
            delayed_shipment_units=shipment_signals.delayed_shipment_units,
        )
        prediction = run_inference(
            {
                "model": self._artifact.model,
                "feature_names": self._artifact.feature_names,
                "version": self._artifact.version,
            },
            feature_vector,
        )

        today = date.today()
        forecast_json = {
            "horizon_days": 7,
            "predictions": [
                {
                    "date": (today + timedelta(days=index + 1)).isoformat(),
                    "units": daily_prediction.units,
                    "lower": daily_prediction.lower,
                    "upper": daily_prediction.upper,
                }
                for index, daily_prediction in enumerate(prediction.daily_predictions)
            ],
            "summary": {
                "total_units": prediction.total_units,
                "avg_daily_units": prediction.avg_daily_units,
                "stockout_risk_pct": prediction.stockout_risk_pct,
                "recommended_reorder_units": prediction.recommended_reorder_units,
            },
        }
        shap_json = {
            "method": "feature_importance_proxy",
            "top_features": [
                {
                    "feature": contribution.feature,
                    "contribution": contribution.contribution,
                }
                for contribution in prediction.top_features
            ],
        }

        return await db_service.save_forecast_run(
            session,
            product=snapshot.product,
            region=snapshot.region,
            forecast_json=forecast_json,
            shap_json=shap_json,
        )
