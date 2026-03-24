"""Analytics routes for SupplyIQ."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_cache_service, get_db
from backend.models.schemas import AlertListResponse, AlertQuery, AnalyticsOverviewResponse, AnalyticsQuery, DemandPoint, SupplierPerformanceResponse
from backend.services import db_service
from backend.services.cache_service import CacheService

router = APIRouter(prefix="/analytics", tags=["analytics"])


def build_analytics_query(
    region_id: Annotated[UUID | None, Query()] = None,
    lookback_days: Annotated[int, Query(ge=7, le=365)] = 30,
) -> AnalyticsQuery:
    """Builds the validated analytics query model."""

    return AnalyticsQuery(region_id=region_id, lookback_days=lookback_days)


def build_alert_query(
    region_id: Annotated[UUID | None, Query()] = None,
    severity: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 6,
) -> AlertQuery:
    """Builds the validated alert query model."""

    return AlertQuery(region_id=region_id, severity=severity, limit=limit)


@router.get("/overview", response_model=AnalyticsOverviewResponse)
async def get_overview(
    query: Annotated[AnalyticsQuery, Depends(build_analytics_query)],
    session: Annotated[AsyncSession, Depends(get_db)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
) -> AnalyticsOverviewResponse:
    """Returns KPI and demand trend data for the analytics overview page."""

    cache_key = cache_service.build_key("analytics_overview", query.model_dump())
    cached = await cache_service.get_json(cache_key)
    if cached is not None:
        return AnalyticsOverviewResponse.model_validate(cached)

    response = AnalyticsOverviewResponse(
        generated_at=datetime.now(timezone.utc),
        region_id=query.region_id,
        kpis=await db_service.build_analytics_kpis(session, region_id=query.region_id),
        demand_series=await db_service.build_demand_series(
            session,
            region_id=query.region_id,
            lookback_days=query.lookback_days,
        ),
    )
    await cache_service.set_json(cache_key, response.model_dump())
    return response


@router.get("/supplier-performance", response_model=SupplierPerformanceResponse)
async def get_supplier_performance(
    query: Annotated[AnalyticsQuery, Depends(build_analytics_query)],
    session: Annotated[AsyncSession, Depends(get_db)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
) -> SupplierPerformanceResponse:
    """Returns supplier reliability and fill-rate analytics."""

    cache_key = cache_service.build_key("supplier_performance", query.model_dump())
    cached = await cache_service.get_json(cache_key)
    if cached is not None:
        return SupplierPerformanceResponse.model_validate(cached)

    response = SupplierPerformanceResponse(
        generated_at=datetime.now(timezone.utc),
        items=await db_service.build_supplier_performance(session, region_id=query.region_id),
    )
    await cache_service.set_json(cache_key, response.model_dump())
    return response


@router.get("/alerts", response_model=AlertListResponse)
async def get_alerts(
    query: Annotated[AlertQuery, Depends(build_alert_query)],
    session: Annotated[AsyncSession, Depends(get_db)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
) -> AlertListResponse:
    """Returns current active alerts for the requested scope."""

    cache_key = cache_service.build_key("alerts", query.model_dump())
    cached = await cache_service.get_json(cache_key)
    if cached is not None:
        return AlertListResponse.model_validate(cached)

    response = AlertListResponse(
        generated_at=datetime.now(timezone.utc),
        items=await db_service.list_alerts(
            session,
            region_id=query.region_id,
            severity=query.severity,
            limit=query.limit,
        ),
    )
    await cache_service.set_json(cache_key, response.model_dump())
    return response
