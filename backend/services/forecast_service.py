"""Forecast orchestration service."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.ml import predict
from backend.models.schemas import ForecastGenerateRequest


class ForecastService:
    """Thin wrapper around the hybrid ML inference pipeline."""

    async def generate_forecast(
        self,
        session: AsyncSession,
        request: ForecastGenerateRequest,
        *,
        user_email: str | None = None,
    ):
        """Generates and persists a seven-day forecast for a product-region pair."""

        return await predict.generate_forecast(
            request.product_id,
            request.region_id,
            session,
            user_email=user_email,
        )
