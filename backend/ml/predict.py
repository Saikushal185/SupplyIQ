"""Inference helpers for SupplyIQ demand forecasting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

FEATURE_NAMES = [
    "current_quantity",
    "reorder_point",
    "unit_cost",
    "avg_units_sold_7d",
    "avg_units_sold_30d",
    "total_revenue_30d",
    "avg_weather_temp_30d",
    "avg_traffic_index_30d",
    "incoming_shipment_units_7d",
    "delayed_shipment_units",
]

DAY_WEIGHTS = [0.13, 0.14, 0.14, 0.15, 0.14, 0.15, 0.15]


@dataclass(slots=True)
class DailyPrediction:
    """Represents a predicted day in the seven-day horizon."""

    units: int
    lower: int
    upper: int


@dataclass(slots=True)
class FeatureContribution:
    """Represents a proxy explanation feature contribution."""

    feature: str
    contribution: float


@dataclass(slots=True)
class PredictionOutput:
    """Represents the normalized output of the demand model."""

    total_units: int
    avg_daily_units: float
    daily_predictions: list[DailyPrediction]
    stockout_risk_pct: float
    recommended_reorder_units: int
    top_features: list[FeatureContribution]


def build_feature_vector(
    *,
    current_quantity: int,
    reorder_point: int,
    unit_cost: float,
    avg_units_sold_7d: float,
    avg_units_sold_30d: float,
    total_revenue_30d: float,
    avg_weather_temp_30d: float,
    avg_traffic_index_30d: float,
    incoming_shipment_units_7d: float,
    delayed_shipment_units: float,
) -> list[float]:
    """Builds the ordered feature vector required by the serialized model."""

    feature_map = {
        "current_quantity": current_quantity,
        "reorder_point": reorder_point,
        "unit_cost": unit_cost,
        "avg_units_sold_7d": avg_units_sold_7d,
        "avg_units_sold_30d": avg_units_sold_30d,
        "total_revenue_30d": total_revenue_30d,
        "avg_weather_temp_30d": avg_weather_temp_30d,
        "avg_traffic_index_30d": avg_traffic_index_30d,
        "incoming_shipment_units_7d": incoming_shipment_units_7d,
        "delayed_shipment_units": delayed_shipment_units,
    }
    return [float(feature_map[name]) for name in FEATURE_NAMES]


def _build_daily_predictions(total_units: int) -> list[DailyPrediction]:
    """Spreads the seven-day demand total into daily slices with confidence bands."""

    predictions: list[DailyPrediction] = []
    allocated_units = 0
    for index, weight in enumerate(DAY_WEIGHTS):
        if index == len(DAY_WEIGHTS) - 1:
            units = max(total_units - allocated_units, 0)
        else:
            units = max(int(round(total_units * weight)), 0)
            allocated_units += units
        uncertainty_band = max(int(round(units * 0.15)), 4)
        predictions.append(
            DailyPrediction(
                units=units,
                lower=max(units - uncertainty_band, 0),
                upper=units + uncertainty_band,
            )
        )
    return predictions


def _build_feature_contributions(model: Any, feature_vector: list[float]) -> list[FeatureContribution]:
    """Builds a proxy explanation payload from model feature importances."""

    importances = list(getattr(model, "feature_importances_", []))
    if len(importances) != len(FEATURE_NAMES):
        importances = [1 / len(FEATURE_NAMES)] * len(FEATURE_NAMES)

    pairs = [
        FeatureContribution(
            feature=feature_name,
            contribution=round(float(abs(feature_value) * importance), 4),
        )
        for feature_name, feature_value, importance in zip(FEATURE_NAMES, feature_vector, importances, strict=True)
    ]
    return sorted(pairs, key=lambda item: item.contribution, reverse=True)[:5]


def run_inference(model_artifact: dict[str, Any], feature_vector: list[float]) -> PredictionOutput:
    """Runs the serialized demand model and derives operational forecast outputs."""

    model = model_artifact["model"]
    predicted_total_units = max(int(round(float(model.predict([feature_vector])[0]))), 0)
    daily_predictions = _build_daily_predictions(predicted_total_units)

    current_quantity = feature_vector[0]
    reorder_point = int(feature_vector[1])
    incoming_supply = feature_vector[8]
    available_supply = current_quantity + incoming_supply
    demand_ratio = predicted_total_units / max(available_supply, 1)
    stockout_risk_pct = min(max((demand_ratio - 0.6) * 90, 5), 99)
    recommended_reorder_units = max(predicted_total_units + reorder_point - int(available_supply), 0)

    return PredictionOutput(
        total_units=predicted_total_units,
        avg_daily_units=round(predicted_total_units / 7, 1),
        daily_predictions=daily_predictions,
        stockout_risk_pct=round(stockout_risk_pct, 2),
        recommended_reorder_units=recommended_reorder_units,
        top_features=_build_feature_contributions(model, feature_vector),
    )
