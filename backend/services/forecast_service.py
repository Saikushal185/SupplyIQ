"""Forecast orchestration service."""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from backend.ml import predict
from backend.models.schemas import ForecastGenerateRequest


class ForecastService:
    """Thin wrapper around the hybrid ML inference pipeline."""

    async def generate_forecast(
        self,
        session: AsyncSession,
        request: ForecastGenerateRequest,
    ):
        """Generates and persists a seven-day forecast for a product-region pair."""

        return await predict.generate_forecast(
            request.product_id,
            request.region_id,
            session,
        )

    async def generate_batch_forecast(
        self,
        session: AsyncSession,
        requests: list[ForecastGenerateRequest],
    ) -> list[object]:
        """Generates forecasts for multiple product-region pairs concurrently."""

        tasks = [
            predict.generate_forecast(req.product_id, req.region_id, session)
            for req in requests
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [
            {"error": str(result)} if isinstance(result, Exception) else result
            for result in results
        ]
