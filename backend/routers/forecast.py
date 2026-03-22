"""Forecast routes for SupplyIQ."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from backend.dependencies import get_db, get_forecast_service
from backend.models.schemas import ForecastGenerateRequest, ForecastHistoryResponse, ForecastPathRequest, ForecastRecordResponse, ProductPathRequest
from backend.services import db_service
from backend.services.forecast_service import ForecastService

router = APIRouter(prefix="/forecast", tags=["forecast"])


def build_forecast_path_request(
    product_id: Annotated[UUID, Path()],
    region_id: Annotated[UUID, Path()],
) -> ForecastPathRequest:
    """Builds the validated forecast path parameter model."""

    return ForecastPathRequest(product_id=product_id, region_id=region_id)


def build_product_path_request(
    product_id: Annotated[UUID, Path()],
) -> ProductPathRequest:
    """Builds the validated product path parameter model."""

    return ProductPathRequest(product_id=product_id)


@router.post("/generate", response_model=ForecastRecordResponse)
def generate_forecast(
    payload: ForecastGenerateRequest,
    session: Annotated[Session, Depends(get_db)],
    forecast_service: Annotated[ForecastService, Depends(get_forecast_service)],
) -> ForecastRecordResponse:
    """Generates and persists a new forecast."""

    try:
        return forecast_service.generate_forecast(session, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/latest/{product_id}/{region_id}", response_model=ForecastRecordResponse)
def get_latest_forecast(
    path_request: Annotated[ForecastPathRequest, Depends(build_forecast_path_request)],
    session: Annotated[Session, Depends(get_db)],
) -> ForecastRecordResponse:
    """Returns the most recently generated forecast for a product-region pair."""

    record = db_service.get_latest_forecast(
        session,
        product_id=path_request.product_id,
        region_id=path_request.region_id,
    )
    if record is None:
        raise HTTPException(status_code=404, detail="No forecast history exists for the requested product and region.")
    return record


@router.get("/history/{product_id}", response_model=ForecastHistoryResponse)
def get_forecast_history(
    path_request: Annotated[ProductPathRequest, Depends(build_product_path_request)],
    session: Annotated[Session, Depends(get_db)],
) -> ForecastHistoryResponse:
    """Returns all stored forecasts for a product."""

    return ForecastHistoryResponse(
        generated_at=datetime.now(timezone.utc),
        items=db_service.get_forecast_history(session, product_id=path_request.product_id),
    )
