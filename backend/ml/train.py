"""Training script for the SupplyIQ hybrid Prophet + XGBoost forecast model."""

from __future__ import annotations

from collections import defaultdict
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any

try:
    import joblib
except ModuleNotFoundError:  # pragma: no cover - dependency exists in the runtime image
    joblib = None  # type: ignore[assignment]

from backend.ml.predict import (
    ARTIFACT_DIR,
    build_feature_matrix,
    build_future_feature_rows,
    build_prophet_artifact_path,
    engineer_history_features,
    summarize_feature_impacts,
    SalesObservation,
)

logger = logging.getLogger(__name__)

XGB_ARTIFACT_PATH = ARTIFACT_DIR / "xgb_residual.joblib"
SHAP_EXPLAINER_ARTIFACT_PATH = ARTIFACT_DIR / "shap_explainer.joblib"


def _require_dependency(module_name: str) -> Any:
    """Imports a training dependency with a helpful failure message."""

    try:
        module = __import__(module_name, fromlist=["*"])
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised in runtime misconfiguration
        raise RuntimeError(f"{module_name} must be installed to train the forecast model.") from exc
    return module


def _get_settings():
    """Imports backend settings lazily so local unit tests can run without full deps."""

    from backend.settings import get_settings

    return get_settings()


def _scope_key(observation: SalesObservation) -> tuple[str, str]:
    """Builds a stable string key for a product-region pair."""

    if observation.product_id is None or observation.region_id is None:
        raise ValueError("Training observations must include product_id and region_id.")
    return str(observation.product_id), str(observation.region_id)


def group_observations_by_scope(
    observations: list[SalesObservation],
) -> dict[tuple[str, str], list[SalesObservation]]:
    """Groups observations by product-region pair for scoped Prophet training."""

    grouped: dict[tuple[str, str], list[SalesObservation]] = defaultdict(list)
    for observation in observations:
        grouped[_scope_key(observation)].append(observation)

    return {
        scope: sorted(scope_observations, key=lambda item: item.sale_date)
        for scope, scope_observations in grouped.items()
    }


def build_residual_training_rows(observations: list[SalesObservation]) -> list[dict[str, object]]:
    """Builds full-history feature rows across all scopes for global XGBoost training."""

    grouped_observations = group_observations_by_scope(observations)
    training_rows: list[dict[str, object]] = []
    for scope in sorted(grouped_observations):
        training_rows.extend(engineer_history_features(grouped_observations[scope]))
    return training_rows


def _load_training_history(*, lookback_days: int = 730) -> list[SalesObservation]:
    """Loads two years of per-scope daily sales from PostgreSQL via SQLAlchemy."""

    sqlalchemy = _require_dependency("sqlalchemy")
    db_models = __import__("backend.models.db_models", fromlist=["DailySale"])

    engine = sqlalchemy.create_engine(_get_settings().database_url, pool_pre_ping=True)
    start_date = date.today() - timedelta(days=lookback_days)
    with engine.connect() as connection:
        statement = (
            sqlalchemy.select(
                db_models.DailySale.product_id,
                db_models.DailySale.region_id,
                db_models.DailySale.sale_date,
                sqlalchemy.func.sum(db_models.DailySale.units_sold).label("units_sold"),
                sqlalchemy.func.avg(db_models.DailySale.weather_temp).label("weather_temp"),
                sqlalchemy.func.avg(db_models.DailySale.traffic_index).label("traffic_index"),
            )
            .where(db_models.DailySale.sale_date >= start_date)
            .group_by(
                db_models.DailySale.product_id,
                db_models.DailySale.region_id,
                db_models.DailySale.sale_date,
            )
            .order_by(
                db_models.DailySale.product_id.asc(),
                db_models.DailySale.region_id.asc(),
                db_models.DailySale.sale_date.asc(),
            )
        )
        rows = connection.execute(statement).all()

    return [
        SalesObservation(
            product_id=product_id,
            region_id=region_id,
            sale_date=sale_date,
            units_sold=float(units_sold or 0),
            weather_temp=float(weather_temp or 0),
            traffic_index=float(traffic_index or 0),
        )
        for product_id, region_id, sale_date, units_sold, weather_temp, traffic_index in rows
    ]


def _build_prophet_frame(history_rows: list[dict[str, object]]) -> Any:
    """Converts engineered rows into the DataFrame Prophet expects."""

    pandas = _require_dependency("pandas")
    return pandas.DataFrame(
        {
            "ds": [row["ds"] for row in history_rows],
            "y": [float(row["y"]) for row in history_rows],
        }
    )


def _fit_prophet(history_rows: list[dict[str, object]]) -> tuple[Any, list[float]]:
    """Fits a scoped Prophet model and returns in-sample yhat predictions."""

    prophet_module = _require_dependency("prophet")
    prophet_model = prophet_module.Prophet(yearly_seasonality=True, weekly_seasonality=True)
    prophet_frame = _build_prophet_frame(history_rows)
    prophet_model.fit(prophet_frame)
    in_sample_forecast = prophet_model.predict(prophet_frame[["ds"]])
    yhat = in_sample_forecast["yhat"].tolist() if hasattr(in_sample_forecast["yhat"], "tolist") else list(in_sample_forecast["yhat"])
    return prophet_model, [float(value) for value in yhat]


def _fit_xgb_residual_model(
    history_rows: list[dict[str, object]],
    prophet_predictions: list[float],
) -> tuple[Any, Any]:
    """Fits the global residual-correction model and its SHAP explainer."""

    xgboost = _require_dependency("xgboost")
    shap = _require_dependency("shap")

    feature_matrix = build_feature_matrix(history_rows)
    residuals = [
        float(row["y"]) - prediction
        for row, prediction in zip(history_rows, prophet_predictions, strict=True)
    ]
    xgb_model = xgboost.XGBRegressor(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        objective="reg:squarederror",
        random_state=42,
    )
    xgb_model.fit(feature_matrix, residuals)
    explainer = shap.TreeExplainer(xgb_model)
    return xgb_model, explainer


def persist_models() -> dict[str, Path]:
    """Trains and serializes the scoped Prophet artifacts plus global residual artifacts."""

    if joblib is None:  # pragma: no cover - exercised only when dependency is absent
        raise RuntimeError("joblib must be installed to persist the forecast artifacts.")

    history = _load_training_history()
    if len(history) < 30:
        raise RuntimeError("At least 30 days of sales history are required to train the forecast model.")

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    grouped_observations = group_observations_by_scope(history)
    if not grouped_observations:
        raise RuntimeError("No product-region sales history was found for training.")

    prophet_artifact_paths: dict[str, Path] = {}
    global_feature_rows: list[dict[str, object]] = []
    global_prophet_predictions: list[float] = []
    preview_feature_rows: list[dict[str, object]] = []

    # Training window: full history (2 years) for seasonal learning
    # Inference window: last 90 days for live feature construction
    for product_region_key in sorted(grouped_observations):
        scoped_observations = grouped_observations[product_region_key]
        scoped_history_rows = engineer_history_features(scoped_observations)
        if len(scoped_history_rows) < 30:
            logger.info(
                "Skipping Prophet training for %s because only %s days were available.",
                product_region_key,
                len(scoped_history_rows),
            )
            continue

        prophet_model, scoped_prophet_predictions = _fit_prophet(scoped_history_rows)
        product_id, region_id = product_region_key
        prophet_artifact_path = build_prophet_artifact_path(product_id, region_id)
        joblib.dump(prophet_model, prophet_artifact_path)
        prophet_artifact_paths[f"{product_id}:{region_id}"] = prophet_artifact_path

        global_feature_rows.extend(scoped_history_rows)
        global_prophet_predictions.extend(scoped_prophet_predictions)

        future_forecast = prophet_model.predict(
            prophet_model.make_future_dataframe(periods=7, include_history=False)
        )
        future_dates = future_forecast["ds"].tolist() if hasattr(future_forecast["ds"], "tolist") else list(future_forecast["ds"])
        future_yhat = future_forecast["yhat"].tolist() if hasattr(future_forecast["yhat"], "tolist") else list(future_forecast["yhat"])
        preview_feature_rows = build_future_feature_rows(
            scoped_history_rows,
            [value.date() if hasattr(value, "date") else value for value in future_dates],
            [float(value) for value in future_yhat],
        )

    if not global_feature_rows:
        raise RuntimeError("No product-region scope had enough history to train Prophet models.")

    xgb_model, explainer = _fit_xgb_residual_model(global_feature_rows, global_prophet_predictions)
    future_shap_values = explainer.shap_values(build_feature_matrix(preview_feature_rows)) if preview_feature_rows else []
    top_features_preview = summarize_feature_impacts(preview_feature_rows, future_shap_values, top_n=5)
    logger.info("Top SHAP features for the next 7-day horizon: %s", top_features_preview)

    joblib.dump(xgb_model, XGB_ARTIFACT_PATH)
    joblib.dump(explainer, SHAP_EXPLAINER_ARTIFACT_PATH)

    artifact_paths = {
        "xgb_residual": XGB_ARTIFACT_PATH,
        "shap_explainer": SHAP_EXPLAINER_ARTIFACT_PATH,
    }
    artifact_paths.update(prophet_artifact_paths)
    return artifact_paths


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    artifact_paths = persist_models()
    for label, artifact_path in artifact_paths.items():
        logger.info("Saved %s artifact to %s", label, artifact_path)
