"""Inference helpers for SupplyIQ demand forecasting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

FEATURE_NAMES = [
    "base_daily_demand",
    "quantity_on_hand",
    "quantity_reserved",
    "inbound_units",
    "reorder_point",
    "unit_cost",
    "supplier_reliability",
    "supplier_lead_time",
    "region_risk_factor",
    "horizon_days",
]


@dataclass(slots=True)
class PredictionOutput:
    """Represents the normalized output of the demand model."""

    predicted_demand_units: int
    lower_bound_units: int
    upper_bound_units: int
    stockout_probability_pct: float
    recommended_reorder_units: int


def build_feature_vector(
    *,
    base_daily_demand: int,
    quantity_on_hand: int,
    quantity_reserved: int,
    inbound_units: int,
    reorder_point: int,
    unit_cost: float,
    supplier_reliability: float,
    supplier_lead_time: int,
    region_risk_factor: float,
    horizon_days: int,
) -> list[float]:
    """Builds the ordered feature vector required by the serialized model."""

    feature_map = {
        "base_daily_demand": base_daily_demand,
        "quantity_on_hand": quantity_on_hand,
        "quantity_reserved": quantity_reserved,
        "inbound_units": inbound_units,
        "reorder_point": reorder_point,
        "unit_cost": unit_cost,
        "supplier_reliability": supplier_reliability,
        "supplier_lead_time": supplier_lead_time,
        "region_risk_factor": region_risk_factor,
        "horizon_days": horizon_days,
    }
    return [float(feature_map[name]) for name in FEATURE_NAMES]


def run_inference(model_artifact: dict[str, Any], feature_vector: list[float]) -> PredictionOutput:
    """Runs the serialized demand model and derives operational forecast bounds."""

    model = model_artifact["model"]
    predicted_value = max(int(round(float(model.predict([feature_vector])[0]))), 0)
    available_units = feature_vector[1] - feature_vector[2] + feature_vector[3]
    reorder_point = int(feature_vector[4])
    demand_ratio = predicted_value / max(available_units, 1)
    stockout_probability_pct = min(max((demand_ratio - 0.7) * 78, 4), 99)
    uncertainty_band = max(int(round(predicted_value * 0.12)), 12)
    recommended_reorder_units = max(predicted_value + reorder_point - int(available_units), 0)

    return PredictionOutput(
        predicted_demand_units=predicted_value,
        lower_bound_units=max(predicted_value - uncertainty_band, 0),
        upper_bound_units=predicted_value + uncertainty_band,
        stockout_probability_pct=round(stockout_probability_pct, 2),
        recommended_reorder_units=recommended_reorder_units,
    )
