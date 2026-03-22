"""Analytics routes for SupplyIQ."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.dependencies import get_cache_service, get_db
from backend.models.schemas import AlertListResponse, AlertQuery, AnalyticsOverviewResponse, AnalyticsQuery, DemandPoint, SupplierPerformanceResponse
from backend.services import db_service
from backend.services.cache_service import CacheService

router = APIRouter(prefix="/analytics", tags=["analytics"])


def build_analytics_query(
    region_code: Annotated[str | None, Query(min_length=2, max_length=32)] = None,
    lookback_days: Annotated[int, Query(ge=7, le=365)] = 30,
) -> AnalyticsQuery:
    """Builds the validated analytics query model."""

    return AnalyticsQuery(region_code=region_code, lookback_days=lookback_days)


def build_alert_query(
    region_code: Annotated[str | None, Query(min_length=2, max_length=32)] = None,
    severity: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 6,
) -> AlertQuery:
    """Builds the validated alert query model."""

    return AlertQuery(region_code=region_code, severity=severity, limit=limit)


@router.get("/overview", response_model=AnalyticsOverviewResponse)
def get_overview(
    query: Annotated[AnalyticsQuery, Depends(build_analytics_query)],
    session: Annotated[Session, Depends(get_db)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
) -> AnalyticsOverviewResponse:
    """Returns KPI and demand trend data for the analytics overview page."""

    cache_key = cache_service.build_key("analytics_overview", query.model_dump())
    cached = cache_service.get_json(cache_key)
    if cached is not None:
        return AnalyticsOverviewResponse.model_validate(cached)

    kpis = db_service.build_analytics_kpis(session, region_code=query.region_code)
    positions = db_service.list_inventory_positions(session, region_code=query.region_code, limit=100)
    base_demand = sum(max(int(item.quantity_on_hand / max(item.days_of_cover, 1)), 1) for item in positions)
    demand_series = [
        DemandPoint(
            label=(datetime.now(timezone.utc) - timedelta(days=index * 7)).strftime("Wk %U"),
            demand_units=int(base_demand * (0.92 + index * 0.03)),
        )
        for index in reversed(range(6))
    ]

    response = AnalyticsOverviewResponse(
        generated_at=datetime.now(timezone.utc),
        region_code=query.region_code,
        kpis=kpis,
        demand_series=demand_series,
    )
    cache_service.set_json(cache_key, response.model_dump())
    return response


@router.get("/supplier-performance", response_model=SupplierPerformanceResponse)
def get_supplier_performance(
    query: Annotated[AnalyticsQuery, Depends(build_analytics_query)],
    session: Annotated[Session, Depends(get_db)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
) -> SupplierPerformanceResponse:
    """Returns supplier reliability and fill-rate analytics."""

    cache_key = cache_service.build_key("supplier_performance", query.model_dump())
    cached = cache_service.get_json(cache_key)
    if cached is not None:
        return SupplierPerformanceResponse.model_validate(cached)

    response = SupplierPerformanceResponse(
        generated_at=datetime.now(timezone.utc),
        items=db_service.build_supplier_performance(session, region_code=query.region_code),
    )
    cache_service.set_json(cache_key, response.model_dump())
    return response


@router.get("/alerts", response_model=AlertListResponse)
def get_alerts(
    query: Annotated[AlertQuery, Depends(build_alert_query)],
    session: Annotated[Session, Depends(get_db)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
) -> AlertListResponse:
    """Returns current active alerts for the requested scope."""

    cache_key = cache_service.build_key("alerts", query.model_dump())
    cached = cache_service.get_json(cache_key)
    if cached is not None:
        return AlertListResponse.model_validate(cached)

    response = AlertListResponse(
        generated_at=datetime.now(timezone.utc),
        items=db_service.list_alerts(
            session,
            region_code=query.region_code,
            severity=query.severity,
            limit=query.limit,
        ),
    )
    cache_service.set_json(cache_key, response.model_dump())
    return response
