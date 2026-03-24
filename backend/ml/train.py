"""One-time training script for the SupplyIQ forecast model."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor

from backend.ml.predict import FEATURE_NAMES

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
ARTIFACT_PATH = ARTIFACT_DIR / "forecast_model.joblib"


def build_training_data(seed: int = 42, sample_size: int = 720) -> tuple[np.ndarray, np.ndarray]:
    """Builds deterministic synthetic training data for demand forecasting."""

    rng = np.random.default_rng(seed)
    current_quantity = rng.integers(60, 2600, sample_size)
    reorder_point = rng.integers(80, 1200, sample_size)
    unit_cost = rng.uniform(4, 380, sample_size)
    avg_units_sold_7d = rng.uniform(10, 210, sample_size)
    avg_units_sold_30d = rng.uniform(8, 190, sample_size)
    total_revenue_30d = rng.uniform(5_000, 120_000, sample_size)
    avg_weather_temp_30d = rng.uniform(18, 103, sample_size)
    avg_traffic_index_30d = rng.uniform(0.05, 0.98, sample_size)
    incoming_shipment_units_7d = rng.integers(0, 1200, sample_size)
    delayed_shipment_units = rng.integers(0, 420, sample_size)

    features = np.column_stack(
        [
            current_quantity,
            reorder_point,
            unit_cost,
            avg_units_sold_7d,
            avg_units_sold_30d,
            total_revenue_30d,
            avg_weather_temp_30d,
            avg_traffic_index_30d,
            incoming_shipment_units_7d,
            delayed_shipment_units,
        ]
    )

    demand_target = (
        avg_units_sold_7d * 4.9
        + avg_units_sold_30d * 1.8
        + incoming_shipment_units_7d * 0.04
        + delayed_shipment_units * 0.06
        + avg_traffic_index_30d * 120
        + np.maximum(reorder_point - current_quantity, 0) * 0.09
        + unit_cost * 0.25
        + avg_weather_temp_30d * 0.6
        + total_revenue_30d / 1800
        + rng.normal(0, 18, sample_size)
    )

    return features, demand_target


def persist_model() -> Path:
    """Trains the demand model and persists it as a joblib artifact."""

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    features, target = build_training_data()
    model = RandomForestRegressor(
        n_estimators=220,
        random_state=42,
        max_depth=10,
        min_samples_leaf=2,
    )
    model.fit(features, target)
    artifact = {
        "model": model,
        "feature_names": FEATURE_NAMES,
        "version": "2026.03.24",
    }
    joblib.dump(artifact, ARTIFACT_PATH)
    return ARTIFACT_PATH


if __name__ == "__main__":
    persist_model()
