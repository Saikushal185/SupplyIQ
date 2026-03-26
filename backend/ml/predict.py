"""Inference helpers for SupplyIQ hybrid demand forecasting."""

from __future__ import annotations

from functools import lru_cache
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from statistics import mean, pstdev
from typing import TYPE_CHECKING, Any, Sequence

try:
    from fastapi import HTTPException
except ModuleNotFoundError:  # pragma: no cover - lightweight fallback for local unit tests
    class HTTPException(Exception):
        """Fallback HTTPException for bare local test environments."""

        def __init__(self, status_code: int, detail: str) -> None:
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

try:
    import joblib
except ModuleNotFoundError:  # pragma: no cover - dependency exists in the runtime image
    joblib = None  # type: ignore[assignment]

if TYPE_CHECKING:  # pragma: no cover - imported only for type checking
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
XGB_ARTIFACT_PATH = ARTIFACT_DIR / "xgb_residual.joblib"
SHAP_EXPLAINER_ARTIFACT_PATH = ARTIFACT_DIR / "shap_explainer.joblib"
MISSING_PROPHET_MODEL_MESSAGE = (
    "No trained model found for this product-region combination. Run train.py first."
)

FEATURE_NAMES = [
    "weather_temp",
    "traffic_index",
    "day_of_week",
    "is_weekend",
    "month",
    "rolling_7d_avg",
    "lag_1",
    "lag_7",
]


@dataclass(slots=True)
class SalesObservation:
    """Represents one aggregated daily sales observation."""

    sale_date: date
    units_sold: float
    weather_temp: float | None
    traffic_index: float | None
    product_id: Any | None = None
    region_id: Any | None = None


def _safe_load_artifact(path: Path) -> Any | None:
    """Loads a joblib artifact when both the dependency and file are available."""

    if joblib is None or not path.exists():
        return None
    try:
        return joblib.load(path)
    except Exception as exc:  # pragma: no cover - exercised in runtime failures
        logger.warning("Unable to load forecast artifact %s: %s", path, exc)
        return None


XGB_RESIDUAL_MODEL = _safe_load_artifact(XGB_ARTIFACT_PATH)
SHAP_EXPLAINER = _safe_load_artifact(SHAP_EXPLAINER_ARTIFACT_PATH)


def build_prophet_artifact_path(product_id: Any, region_id: Any) -> Path:
    """Builds the scoped Prophet artifact path for a product-region pair."""

    return ARTIFACT_DIR / f"prophet_{product_id}_{region_id}.joblib"


@lru_cache(maxsize=512)
def load_prophet_model_for_scope(product_id: Any, region_id: Any) -> Any:
    """Loads the scoped Prophet model for a product-region pair."""

    artifact_path = build_prophet_artifact_path(product_id, region_id)
    if not artifact_path.exists():
        raise HTTPException(status_code=404, detail=MISSING_PROPHET_MODEL_MESSAGE)
    if joblib is None:  # pragma: no cover - exercised only when dependency is absent
        raise RuntimeError("joblib must be installed to load Prophet forecast artifacts.")

    try:
        return joblib.load(artifact_path)
    except FileNotFoundError as exc:  # pragma: no cover - defensive race-condition guard
        raise HTTPException(status_code=404, detail=MISSING_PROPHET_MODEL_MESSAGE) from exc
    except Exception as exc:  # pragma: no cover - exercised in runtime failures
        logger.warning("Unable to load Prophet artifact %s: %s", artifact_path, exc)
        raise RuntimeError(f"Unable to load Prophet forecast artifact: {artifact_path}") from exc


def _coerce_float(value: object, default: float = 0.0) -> float:
    """Normalizes a database or model value into a float."""

    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_date(value: object) -> date:
    """Normalizes Prophet and SQLAlchemy date values into plain dates."""

    if isinstance(value, date):
        return value
    if hasattr(value, "date"):
        return value.date()  # type: ignore[return-value]
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError(f"Unsupported date value: {value!r}")


def _date_range(start_date: date, end_date: date) -> list[date]:
    """Returns an inclusive list of dates."""

    total_days = (end_date - start_date).days
    return [start_date + timedelta(days=offset) for offset in range(total_days + 1)]


def build_dense_history(observations: Sequence[SalesObservation]) -> list[SalesObservation]:
    """Fills missing calendar days so lag features remain aligned."""

    if not observations:
        return []

    sorted_observations = sorted(observations, key=lambda item: item.sale_date)
    observation_by_date = {item.sale_date: item for item in sorted_observations}
    overall_avg_temp = mean(_coerce_float(item.weather_temp) for item in sorted_observations)
    overall_avg_traffic = mean(_coerce_float(item.traffic_index) for item in sorted_observations)

    dense_rows: list[SalesObservation] = []
    last_temp = overall_avg_temp
    last_traffic = overall_avg_traffic
    for current_date in _date_range(sorted_observations[0].sale_date, sorted_observations[-1].sale_date):
        observation = observation_by_date.get(current_date)
        if observation is None:
            dense_rows.append(
                SalesObservation(
                    sale_date=current_date,
                    units_sold=0.0,
                    weather_temp=last_temp,
                    traffic_index=last_traffic,
                )
            )
            continue

        resolved_temp = _coerce_float(observation.weather_temp, last_temp)
        resolved_traffic = _coerce_float(observation.traffic_index, last_traffic)
        dense_rows.append(
            SalesObservation(
                sale_date=current_date,
                units_sold=_coerce_float(observation.units_sold),
                weather_temp=resolved_temp,
                traffic_index=resolved_traffic,
            )
        )
        last_temp = resolved_temp
        last_traffic = resolved_traffic

    return dense_rows


def engineer_history_features(observations: Sequence[SalesObservation]) -> list[dict[str, object]]:
    """Builds the feature rows used for XGBoost residual learning."""

    dense_history = build_dense_history(observations)
    prior_units: list[float] = []
    feature_rows: list[dict[str, object]] = []

    for observation in dense_history:
        day_of_week = observation.sale_date.weekday()
        feature_rows.append(
            {
                "ds": observation.sale_date,
                "y": _coerce_float(observation.units_sold),
                "weather_temp": _coerce_float(observation.weather_temp),
                "traffic_index": _coerce_float(observation.traffic_index),
                "day_of_week": day_of_week,
                "is_weekend": day_of_week >= 5,
                "month": observation.sale_date.month,
                # Rolling averages are based on prior days to avoid target leakage.
                "rolling_7d_avg": mean(prior_units[-7:]) if prior_units else 0.0,
                "lag_1": prior_units[-1] if prior_units else 0.0,
                "lag_7": prior_units[-7] if len(prior_units) >= 7 else 0.0,
            }
        )
        prior_units.append(_coerce_float(observation.units_sold))

    return feature_rows


def _forecast_exogenous_signal(
    history_rows: Sequence[dict[str, object]],
    future_rows: Sequence[dict[str, object]],
    *,
    feature_name: str,
    target_date: date,
) -> float:
    """Projects future weather and traffic using same-weekday history when available."""

    all_rows = [*history_rows, *future_rows]
    same_weekday_values = [
        _coerce_float(row.get(feature_name))
        for row in all_rows
        if row.get("day_of_week") == target_date.weekday()
    ]
    if same_weekday_values:
        return round(mean(same_weekday_values[-8:]), 4)

    trailing_values = [_coerce_float(row.get(feature_name)) for row in history_rows[-14:]]
    if trailing_values:
        return round(mean(trailing_values), 4)

    return 0.0


def build_future_feature_rows(
    history_rows: Sequence[dict[str, object]],
    future_dates: Sequence[date],
    future_units: Sequence[float],
) -> list[dict[str, object]]:
    """Builds recursive future feature rows using known history and prior predictions."""

    if len(future_dates) != len(future_units):
        raise ValueError("future_dates and future_units must have matching lengths.")

    known_units = [_coerce_float(row.get("y")) for row in history_rows]
    future_rows: list[dict[str, object]] = []

    for forecast_date, forecast_units in zip(future_dates, future_units, strict=True):
        day_of_week = forecast_date.weekday()
        future_rows.append(
            {
                "ds": forecast_date,
                "y": _coerce_float(forecast_units),
                "weather_temp": _forecast_exogenous_signal(
                    history_rows,
                    future_rows,
                    feature_name="weather_temp",
                    target_date=forecast_date,
                ),
                "traffic_index": _forecast_exogenous_signal(
                    history_rows,
                    future_rows,
                    feature_name="traffic_index",
                    target_date=forecast_date,
                ),
                "day_of_week": day_of_week,
                "is_weekend": day_of_week >= 5,
                "month": forecast_date.month,
                "rolling_7d_avg": mean(known_units[-7:]) if known_units else 0.0,
                "lag_1": known_units[-1] if known_units else 0.0,
                "lag_7": known_units[-7] if len(known_units) >= 7 else 0.0,
            }
        )
        known_units.append(_coerce_float(forecast_units))

    return future_rows


def build_feature_matrix(feature_rows: Sequence[dict[str, object]]) -> list[list[float]]:
    """Converts feature rows into the XGBoost input matrix."""

    return [
        [
            _coerce_float(row.get("weather_temp")),
            _coerce_float(row.get("traffic_index")),
            _coerce_float(row.get("day_of_week")),
            1.0 if bool(row.get("is_weekend")) else 0.0,
            _coerce_float(row.get("month")),
            _coerce_float(row.get("rolling_7d_avg")),
            _coerce_float(row.get("lag_1")),
            _coerce_float(row.get("lag_7")),
        ]
        for row in feature_rows
    ]


def summarize_feature_impacts(
    feature_rows: Sequence[dict[str, object]],
    shap_values: Sequence[Sequence[float]] | Sequence[float],
    *,
    top_n: int = 5,
) -> list[dict[str, object]]:
    """Aggregates SHAP values across the forecast horizon into a top-five payload."""

    if not feature_rows:
        return []

    normalized_shap_values = _normalize_shap_values(shap_values)
    if not normalized_shap_values:
        return []

    top_features: list[dict[str, object]] = []
    for feature_index, feature_name in enumerate(FEATURE_NAMES):
        per_day_values = [row[feature_index] for row in normalized_shap_values if len(row) > feature_index]
        if not per_day_values:
            continue

        direction = "up" if mean(per_day_values) >= 0 else "down"
        feature_value = mean(_coerce_float(row.get(feature_name)) for row in feature_rows)
        top_features.append(
            {
                "feature": feature_name,
                "value": round(feature_value, 4),
                "direction": direction,
                "contribution": round(mean(abs(value) for value in per_day_values), 4),
            }
        )

    return sorted(top_features, key=lambda item: item["contribution"], reverse=True)[:top_n]


def detect_stockout_risk(
    *,
    current_inventory: int,
    reorder_point: int | None,
    forecast_days: Sequence[dict[str, object]],
    safety_multiplier: float = 1.2,
) -> dict[str, object] | None:
    """Returns the first forecast day that would put the product into a stockout risk window."""

    remaining_inventory = float(current_inventory)
    for forecast_day in forecast_days:
        predicted_units = _coerce_float(forecast_day.get("predicted_units"))
        if remaining_inventory <= _coerce_float(reorder_point) or remaining_inventory < predicted_units * safety_multiplier:
            return {
                "stockout_date": str(forecast_day["date"]),
                "current_stock_level": int(round(current_inventory)),
                "remaining_inventory": int(round(remaining_inventory)),
                "reorder_point": int(round(_coerce_float(reorder_point))),
            }
        remaining_inventory -= predicted_units

    return None


def _normalize_prediction_bounds(predicted_units: float, lower_bound: float, upper_bound: float) -> tuple[int, int, int]:
    """Normalizes forecast values into integer units with sane bounds."""

    rounded_prediction = max(int(round(predicted_units)), 0)
    rounded_lower = max(int(round(lower_bound)), 0)
    rounded_upper = max(int(round(upper_bound)), rounded_prediction, rounded_lower)
    return rounded_prediction, rounded_lower, rounded_upper


def _normalize_shap_values(shap_values: Sequence[Sequence[float]] | Sequence[float] | Any) -> list[list[float]]:
    """Converts SHAP outputs into a nested Python list."""

    if shap_values is None:
        return []
    if hasattr(shap_values, "tolist"):
        shap_values = shap_values.tolist()
    if isinstance(shap_values, list) and shap_values and not isinstance(shap_values[0], list):
        return [[_coerce_float(value) for value in shap_values]]
    if isinstance(shap_values, Sequence):
        return [[_coerce_float(value) for value in row] for row in shap_values]
    return []


def _forecast_prophet_baseline(prophet_model: Any, *, periods: int = 7) -> list[dict[str, object]]:
    """Uses the serialized Prophet baseline model to forecast the next seven days."""

    if prophet_model is None:
        raise RuntimeError(
            "Prophet artifact is not loaded. Train the hybrid model before generating forecasts."
        )

    future_frame = prophet_model.make_future_dataframe(periods=periods, include_history=False)
    forecast_frame = prophet_model.predict(future_frame)
    records = forecast_frame.to_dict("records") if hasattr(forecast_frame, "to_dict") else list(forecast_frame)
    return [
        {
            "date": _coerce_date(record["ds"]).isoformat(),
            "yhat": _coerce_float(record.get("yhat")),
            "yhat_lower": _coerce_float(record.get("yhat_lower"), _coerce_float(record.get("yhat")) * 0.9),
            "yhat_upper": _coerce_float(record.get("yhat_upper"), _coerce_float(record.get("yhat")) * 1.1),
        }
        for record in records[-periods:]
    ]


def _predict_residual_corrections(xgb_model: Any, future_feature_rows: Sequence[dict[str, object]]) -> list[float]:
    """Predicts residual corrections for the future feature matrix."""

    if xgb_model is None:
        raise RuntimeError(
            "XGBoost residual artifact is not loaded. Train the hybrid model before generating forecasts."
        )

    matrix = build_feature_matrix(future_feature_rows)
    raw_predictions = xgb_model.predict(matrix)
    if hasattr(raw_predictions, "tolist"):
        raw_predictions = raw_predictions.tolist()
    return [_coerce_float(value) for value in raw_predictions]


def _compute_shap_values(explainer: Any, future_feature_rows: Sequence[dict[str, object]]) -> list[list[float]]:
    """Runs SHAP explainability against the future feature matrix."""

    if explainer is None:
        raise RuntimeError(
            "SHAP explainer artifact is not loaded. Train the hybrid model before generating forecasts."
        )

    matrix = build_feature_matrix(future_feature_rows)
    if hasattr(explainer, "shap_values"):
        shap_values = explainer.shap_values(matrix)
    else:  # pragma: no cover - alternate SHAP calling contract
        shap_values = explainer(matrix)
        if hasattr(shap_values, "values"):
            shap_values = shap_values.values
    return _normalize_shap_values(shap_values)


def _build_forecast_rows(
    prophet_rows: Sequence[dict[str, object]],
    residual_predictions: Sequence[float],
) -> list[dict[str, object]]:
    """Combines Prophet and XGBoost outputs into the persisted seven-day forecast."""

    combined_rows: list[dict[str, object]] = []
    for prophet_row, residual_prediction in zip(prophet_rows, residual_predictions, strict=True):
        predicted_units, lower_bound, upper_bound = _normalize_prediction_bounds(
            _coerce_float(prophet_row.get("yhat")) + residual_prediction,
            _coerce_float(prophet_row.get("yhat_lower")) + residual_prediction,
            _coerce_float(prophet_row.get("yhat_upper")) + residual_prediction,
        )
        combined_rows.append(
            {
                "date": str(prophet_row["date"]),
                "predicted_units": predicted_units,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                # Compatibility fields for the current frontend payload.
                "units": predicted_units,
                "lower": lower_bound,
                "upper": upper_bound,
            }
        )

    return combined_rows


def _build_fallback_forecast_rows(
    recent_history: Sequence[SalesObservation],
    *,
    horizon_days: int = 7,
) -> list[dict[str, object]]:
    """Builds a heuristic forecast when trained ML artifacts are unavailable."""

    dense_history = build_dense_history(recent_history)
    trailing_units = [_coerce_float(row.units_sold) for row in dense_history[-28:]]
    last_observation_date = dense_history[-1].sale_date
    recent_avg = mean(trailing_units[-7:]) if trailing_units[-7:] else mean(trailing_units)
    prior_window = trailing_units[-14:-7]
    momentum = recent_avg - (mean(prior_window) if prior_window else recent_avg)
    variability = pstdev(trailing_units[-14:]) if len(trailing_units[-14:]) > 1 else max(recent_avg * 0.12, 1.0)

    rows: list[dict[str, object]] = []
    for offset in range(1, horizon_days + 1):
        forecast_date = last_observation_date + timedelta(days=offset)
        same_weekday_values = [
            _coerce_float(observation.units_sold)
            for observation in dense_history
            if observation.sale_date.weekday() == forecast_date.weekday()
        ][-6:]
        seasonal_baseline = mean(same_weekday_values) if same_weekday_values else recent_avg
        predicted_units, lower_bound, upper_bound = _normalize_prediction_bounds(
            seasonal_baseline + (momentum * 0.35),
            seasonal_baseline - variability,
            seasonal_baseline + variability * 1.15,
        )
        rows.append(
            {
                "date": forecast_date.isoformat(),
                "predicted_units": predicted_units,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "units": predicted_units,
                "lower": lower_bound,
                "upper": upper_bound,
            }
        )

    return rows


def _build_fallback_top_features(
    recent_history: Sequence[SalesObservation],
    history_rows: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """Builds a compact explanation payload for heuristic local forecasts."""

    dense_history = build_dense_history(recent_history)
    trailing_units = [_coerce_float(observation.units_sold) for observation in dense_history[-28:]]
    recent_avg = mean(trailing_units[-7:]) if trailing_units[-7:] else mean(trailing_units)
    previous_avg = mean(trailing_units[-14:-7]) if trailing_units[-14:-7] else recent_avg
    weekend_values = [
        _coerce_float(observation.units_sold)
        for observation in dense_history[-28:]
        if observation.sale_date.weekday() >= 5
    ]
    weekday_values = [
        _coerce_float(observation.units_sold)
        for observation in dense_history[-28:]
        if observation.sale_date.weekday() < 5
    ]
    recent_feature_rows = history_rows[-14:] if history_rows else []
    average_traffic = mean(_coerce_float(row.get("traffic_index")) for row in recent_feature_rows) if recent_feature_rows else 0.0
    average_weather = mean(_coerce_float(row.get("weather_temp")) for row in recent_feature_rows) if recent_feature_rows else 0.0

    candidate_features = [
        {
            "feature": "recent_demand_momentum",
            "value": round(recent_avg - previous_avg, 4),
            "direction": "up" if recent_avg >= previous_avg else "down",
            "contribution": round(abs(recent_avg - previous_avg), 4),
        },
        {
            "feature": "weekend_pattern",
            "value": round((mean(weekend_values) if weekend_values else recent_avg), 4),
            "direction": "up" if (mean(weekend_values) if weekend_values else recent_avg) >= (mean(weekday_values) if weekday_values else recent_avg) else "down",
            "contribution": round(abs((mean(weekend_values) if weekend_values else recent_avg) - (mean(weekday_values) if weekday_values else recent_avg)), 4),
        },
        {
            "feature": "traffic_index",
            "value": round(average_traffic, 4),
            "direction": "up" if average_traffic >= 1 else "down",
            "contribution": round(abs(average_traffic - 1) * max(recent_avg, 1), 4),
        },
        {
            "feature": "weather_temp",
            "value": round(average_weather, 4),
            "direction": "up" if average_weather >= 65 else "down",
            "contribution": round(abs(average_weather - 65) / 10, 4),
        },
        {
            "feature": "rolling_7d_avg",
            "value": round(recent_avg, 4),
            "direction": "up",
            "contribution": round(recent_avg, 4),
        },
    ]
    return sorted(candidate_features, key=lambda item: item["contribution"], reverse=True)[:5]


def _should_use_fallback(exc: Exception) -> bool:
    """Returns whether a runtime failure should switch to the heuristic fallback."""

    message = str(exc).lower()
    if isinstance(exc, HTTPException) and getattr(exc, "detail", "") == MISSING_PROPHET_MODEL_MESSAGE:
        return True
    return any(
        token in message
        for token in (
            "train the hybrid model",
            "joblib must be installed",
            "artifact",
            "no trained model found",
        )
    )


def _build_forecast_summary(
    *,
    forecast_days: Sequence[dict[str, object]],
    current_inventory: int,
    reorder_point: int | None,
    stockout_risk: dict[str, object] | None,
) -> dict[str, object]:
    """Builds operational summary metrics for the response payload."""

    total_units = sum(int(_coerce_float(day.get("predicted_units"))) for day in forecast_days)
    avg_daily_units = round(total_units / max(len(forecast_days), 1), 1)
    demand_pressure = total_units / max(current_inventory, 1)
    stockout_risk_pct = min(max(demand_pressure * 70, 5), 99)
    if stockout_risk is not None:
        stockout_risk_pct = max(stockout_risk_pct, 85.0)

    recommended_reorder_units = max(int(round(total_units * 1.2)) - current_inventory, 0)
    if reorder_point is not None:
        recommended_reorder_units = max(recommended_reorder_units, max(reorder_point - current_inventory, 0))

    return {
        "total_units": total_units,
        "avg_daily_units": avg_daily_units,
        "stockout_risk_pct": round(stockout_risk_pct, 2),
        "recommended_reorder_units": recommended_reorder_units,
    }


async def _load_recent_sales_history(
    db_session: AsyncSession,
    *,
    product_id: Any,
    region_id: Any,
    lookback_days: int = 90,
) -> list[SalesObservation]:
    """Loads the last 90 days of aggregated sales for a product-region pair."""

    from sqlalchemy import func, select

    from backend.models.db_models import DailySale

    start_date = date.today() - timedelta(days=lookback_days)
    statement = (
        select(
            DailySale.sale_date,
            func.sum(DailySale.units_sold).label("units_sold"),
            func.avg(DailySale.weather_temp).label("weather_temp"),
            func.avg(DailySale.traffic_index).label("traffic_index"),
        )
        .where(
            DailySale.product_id == product_id,
            DailySale.region_id == region_id,
            DailySale.sale_date >= start_date,
        )
        .group_by(DailySale.sale_date)
        .order_by(DailySale.sale_date.asc())
    )
    rows = (await db_session.execute(statement)).all()
    return [
        SalesObservation(
            sale_date=sale_date,
            units_sold=_coerce_float(units_sold),
            weather_temp=_coerce_float(weather_temp),
            traffic_index=_coerce_float(traffic_index),
        )
        for sale_date, units_sold, weather_temp, traffic_index in rows
    ]


async def _load_inventory_context(
    db_session: AsyncSession,
    *,
    product_id: Any,
    region_id: Any,
) -> Any:
    """Loads the latest inventory context for a product-region pair."""

    from backend.services import db_service

    return await db_service.get_inventory_context(
        db_session,
        product_id=product_id,
        region_id=region_id,
    )


async def _save_forecast_run(
    db_session: AsyncSession,
    *,
    product: Any,
    region: Any,
    forecast_json: dict[str, object],
    shap_json: dict[str, object],
) -> Any:
    """Persists the hybrid forecast output."""

    from backend.services import db_service

    return await db_service.save_forecast_run(
        db_session,
        product=product,
        region=region,
        forecast_json=forecast_json,
        shap_json=shap_json,
    )


async def generate_forecast(
    product_id: Any,
    region_id: Any,
    db_session: AsyncSession,
    *,
    user_email: str | None = None,
    prophet_model: Any | None = None,
    xgb_model: Any | None = None,
    explainer: Any | None = None,
    email_sender: Any | None = None,
) -> Any:
    """Generates, explains, persists, and alerts on a seven-day forecast."""

    inventory_context = await _load_inventory_context(
        db_session,
        product_id=product_id,
        region_id=region_id,
    )
    recent_history = await _load_recent_sales_history(
        db_session,
        product_id=product_id,
        region_id=region_id,
    )
    if len(recent_history) < 7:
        raise LookupError("At least 7 days of sales history are required to generate a forecast.")

    history_rows = engineer_history_features(recent_history)
    forecast_method = "shap_tree_explainer"

    try:
        prophet_rows = _forecast_prophet_baseline(
            prophet_model or load_prophet_model_for_scope(product_id, region_id),
            periods=7,
        )
        future_dates = [_coerce_date(row["date"]) for row in prophet_rows]
        baseline_predictions = [_coerce_float(row.get("yhat")) for row in prophet_rows]
        future_feature_rows = build_future_feature_rows(history_rows, future_dates, baseline_predictions)
        residual_predictions = _predict_residual_corrections(
            xgb_model or XGB_RESIDUAL_MODEL,
            future_feature_rows,
        )
        shap_values = _compute_shap_values(explainer or SHAP_EXPLAINER, future_feature_rows)
        forecast_days = _build_forecast_rows(prophet_rows, residual_predictions)
        top_features = summarize_feature_impacts(future_feature_rows, shap_values, top_n=5)
    except Exception as exc:
        if not _should_use_fallback(exc):
            raise
        logger.info(
            "Falling back to heuristic forecast generation for product %s and region %s: %s",
            product_id,
            region_id,
            exc,
        )
        forecast_method = "heuristic_local_fallback"
        future_feature_rows = []
        forecast_days = _build_fallback_forecast_rows(recent_history, horizon_days=7)
        top_features = _build_fallback_top_features(recent_history, history_rows)

    stockout_risk = detect_stockout_risk(
        current_inventory=int(inventory_context.quantity),
        reorder_point=getattr(inventory_context.product, "reorder_point", None),
        forecast_days=forecast_days,
    )

    forecast_json = {
        "horizon_days": 7,
        "predictions": forecast_days,
        "summary": _build_forecast_summary(
            forecast_days=forecast_days,
            current_inventory=int(inventory_context.quantity),
            reorder_point=getattr(inventory_context.product, "reorder_point", None),
            stockout_risk=stockout_risk,
        ),
    }
    shap_json = {
        "method": forecast_method,
        "top_features": top_features,
    }

    if stockout_risk is not None and user_email:
        if email_sender is None:
            from pipeline.flows.alert_flow import send_stockout_risk_email

            email_sender = send_stockout_risk_email

        try:
            await email_sender(
                recipient_email=user_email,
                product_name=str(inventory_context.product.name),
                region_name=str(inventory_context.region.name),
                stockout_date=str(stockout_risk["stockout_date"]),
                current_stock_level=int(stockout_risk["current_stock_level"]),
            )
        except Exception as exc:  # pragma: no cover - exercised with networked integrations
            logger.warning("Unable to send stockout alert email: %s", exc)

    return await _save_forecast_run(
        db_session,
        product=inventory_context.product,
        region=inventory_context.region,
        forecast_json=forecast_json,
        shap_json=shap_json,
    )
