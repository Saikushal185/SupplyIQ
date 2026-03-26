"""Forecast routes for SupplyIQ."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import AuthContext, get_current_user_email, get_db, get_forecast_service, require_roles
from backend.models.schemas import ForecastGenerateRequest
from backend.services import db_service
from backend.services.forecast_service import ForecastService
from backend.services.response_service import build_response

router = APIRouter(prefix="/forecast", tags=["forecast"])

forecast_access = require_roles("admin", "analyst")


@router.post("/generate")
async def generate_forecast(
    payload: ForecastGenerateRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    forecast_service: Annotated[ForecastService, Depends(get_forecast_service)],
    user_email: Annotated[str | None, Depends(get_current_user_email)],
    _: Annotated[AuthContext, Depends(forecast_access)],
):
    """Generates and persists a new forecast for a product-region pair."""

    try:
        data = await forecast_service.generate_forecast(session, payload, user_email=user_email)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return build_response(data)


@router.get("/latest/{product_id}/{region_id}")
async def get_latest_forecast(
    product_id: UUID,
    region_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[AuthContext, Depends(forecast_access)],
):
    """Returns the most recent forecast run for a product-region pair."""

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
    product_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[AuthContext, Depends(forecast_access)],
):
    """Returns the stored forecast history for a product across regions."""

    data = await db_service.get_forecast_history(session, product_id=product_id)
    return build_response(data)
