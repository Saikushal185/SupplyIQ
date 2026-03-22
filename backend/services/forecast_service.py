"""Forecast model loading and inference service."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
from sqlalchemy.orm import Session

from backend.ml.predict import build_feature_vector, run_inference
from backend.models.schemas import ForecastGenerateRequest, ForecastRecordResponse
from backend.services import db_service


@dataclass(slots=True)
class ForecastArtifact:
    """Represents a loaded serialized forecast model artifact."""

    model: Any
    feature_names: list[str]
    version: str


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

    def generate_forecast(
        self,
        session: Session,
        request: ForecastGenerateRequest,
    ) -> ForecastRecordResponse:
        """Generates and persists a forecast for a single product-region pair."""

        snapshot, product, region, supplier = db_service.get_inventory_context(
            session,
            product_id=request.product_id,
            region_id=request.region_id,
        )
        feature_vector = build_feature_vector(
            base_daily_demand=product.base_daily_demand,
            quantity_on_hand=snapshot.quantity_on_hand,
            quantity_reserved=snapshot.quantity_reserved,
            inbound_units=snapshot.inbound_units,
            reorder_point=product.reorder_point,
            unit_cost=float(product.unit_cost),
            supplier_reliability=float(supplier.reliability_score),
            supplier_lead_time=supplier.lead_time_days,
            region_risk_factor=float(region.risk_factor),
            horizon_days=request.horizon_days,
        )
        prediction = run_inference(
            {
                "model": self._artifact.model,
                "feature_names": self._artifact.feature_names,
                "version": self._artifact.version,
            },
            feature_vector,
        )
        return db_service.save_forecast_run(
            session,
            product=product,
            region=region,
            horizon_days=request.horizon_days,
            predicted_demand_units=prediction.predicted_demand_units,
            lower_bound_units=prediction.lower_bound_units,
            upper_bound_units=prediction.upper_bound_units,
            stockout_probability_pct=prediction.stockout_probability_pct,
            recommended_reorder_units=prediction.recommended_reorder_units,
            model_version=self._artifact.version,
        )
