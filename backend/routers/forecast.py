"""Forecast routes for SupplyIQ."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_db, get_forecast_service
from backend.models.schemas import ForecastGenerateRequest
from backend.services import db_service
from backend.services.forecast_service import ForecastService
from backend.services.response_service import build_response

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.post("/generate")
async def generate_forecast(
    payload: ForecastGenerateRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    forecast_service: Annotated[ForecastService, Depends(get_forecast_service)],
):
    """Generates and persists a new forecast."""

    try:
        data = await forecast_service.generate_forecast(session, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return build_response(data)


@router.post("/batch")
async def generate_batch_forecast(
    payloads: list[ForecastGenerateRequest],
    session: Annotated[AsyncSession, Depends(get_db)],
    forecast_service: Annotated[ForecastService, Depends(get_forecast_service)],
):
    """Generates forecasts for multiple product-region pairs in a single request."""

    if not payloads:
        raise HTTPException(status_code=422, detail="At least one forecast request is required.")
    results = await forecast_service.generate_batch_forecast(session, payloads)
    return build_response(results)


@router.get("/latest/{product_id}/{region_id}")
async def get_latest_forecast(
    product_id: Annotated[UUID, Path()],
    region_id: Annotated[UUID, Path()],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """Returns the most recently generated forecast for a product-region pair."""

    record = await db_service.get_latest_forecast(
        session,
        product_id=product_id,
        region_id=region_id,
    )
    if record is None:
        raise HTTPException(status_code=404, detail="No forecast history exists for the requested product and region.")
    return build_response(record)


@router.get("/history/{product_id}")
async def get_forecast_history(
    product_id: Annotated[UUID, Path()],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """Returns all stored forecasts for a product."""

    data = await db_service.get_forecast_history(session, product_id=product_id)
    return build_response(data)
