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
    base_daily_demand = rng.integers(12, 190, sample_size)
    quantity_on_hand = rng.integers(80, 3200, sample_size)
    quantity_reserved = rng.integers(0, 400, sample_size)
    inbound_units = rng.integers(0, 900, sample_size)
    reorder_point = rng.integers(50, 1200, sample_size)
    unit_cost = rng.uniform(4, 380, sample_size)
    supplier_reliability = rng.uniform(0.75, 0.99, sample_size)
    supplier_lead_time = rng.integers(4, 28, sample_size)
    region_risk_factor = rng.uniform(0.2, 0.95, sample_size)
    horizon_days = rng.integers(7, 91, sample_size)

    features = np.column_stack(
        [
            base_daily_demand,
            quantity_on_hand,
            quantity_reserved,
            inbound_units,
            reorder_point,
            unit_cost,
            supplier_reliability,
            supplier_lead_time,
            region_risk_factor,
            horizon_days,
        ]
    )

    demand_target = (
        base_daily_demand * horizon_days * (1.01 + (1 - supplier_reliability) * 0.08)
        + region_risk_factor * 40
        + np.maximum(quantity_reserved - inbound_units, 0) * 0.18
        + supplier_lead_time * 1.5
        + rng.normal(0, 28, sample_size)
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
        "version": "2026.03.22",
    }
    joblib.dump(artifact, ARTIFACT_PATH)
    return ARTIFACT_PATH


if __name__ == "__main__":
    persist_model()
