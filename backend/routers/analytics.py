"""Analytics routes for SupplyIQ."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_cache_service, get_db
from backend.services import db_service
from backend.services.analytics_service import get_analytics_filter_options, get_regional_growth
from backend.services.cache_service import CacheService
from backend.services.response_service import build_response

router = APIRouter(prefix="/analytics", tags=["analytics"])


async def _load_cached_analytics_payload(
    *,
    cache_service: CacheService,
    namespace: str,
    payload: dict[str, object],
    loader,
):
    """Returns a cached analytics response when available, otherwise stores a fresh one."""

    cache_key = cache_service.build_key(namespace, payload)
    cached = await cache_service.get_json(cache_key)
    if cached is not None:
        return build_response(cached, cached=True)

    data = await loader()
    await cache_service.set_json(cache_key, data)
    return build_response(data, cached=False)


@router.get("/sales")
async def get_sales(
    session: Annotated[AsyncSession, Depends(get_db)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    region_id: Annotated[UUID | None, Query()] = None,
):
    """Returns daily sales aggregated by region for the requested date range."""

    try:
        return await _load_cached_analytics_payload(
            cache_service=cache_service,
            namespace="analytics.sales",
            payload={
                "start_date": start_date,
                "end_date": end_date,
                "region_id": region_id,
            },
            loader=lambda: db_service.get_sales_analytics(
                session,
                start_date=start_date,
                end_date=end_date,
                region_id=region_id,
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/filters")
async def get_filters(
    session: Annotated[AsyncSession, Depends(get_db)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
):
    """Returns region, product, and category options for analytics filters."""

    return await _load_cached_analytics_payload(
        cache_service=cache_service,
        namespace="analytics.filters",
        payload={},
        loader=lambda: get_analytics_filter_options(session),
    )


@router.get("/product-sales")
async def get_product_sales(
    session: Annotated[AsyncSession, Depends(get_db)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    region_id: Annotated[UUID | None, Query()] = None,
    category: Annotated[str | None, Query()] = None,
):
    """Returns product-level sales summaries for the requested filters."""

    try:
        return await _load_cached_analytics_payload(
            cache_service=cache_service,
            namespace="analytics.product-sales",
            payload={
                "start_date": start_date,
                "end_date": end_date,
                "region_id": region_id,
                "category": category,
            },
            loader=lambda: db_service.get_product_sales_summary(
                session,
                start_date=start_date,
                end_date=end_date,
                region_id=region_id,
                category=category,
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/turnover")
async def get_turnover(
    session: Annotated[AsyncSession, Depends(get_db)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
):
    """Returns inventory turnover ratios by product."""

    try:
        return await _load_cached_analytics_payload(
            cache_service=cache_service,
            namespace="analytics.turnover",
            payload={
                "start_date": start_date,
                "end_date": end_date,
            },
            loader=lambda: db_service.get_inventory_turnover(
                session,
                start_date=start_date,
                end_date=end_date,
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/supplier-reliability")
async def get_supplier_reliability(
    session: Annotated[AsyncSession, Depends(get_db)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
    region_id: Annotated[UUID | None, Query()] = None,
):
    """Returns on-time supplier delivery performance."""

    return await _load_cached_analytics_payload(
        cache_service=cache_service,
        namespace="analytics.supplier-reliability",
        payload={"region_id": region_id},
        loader=lambda: db_service.get_supplier_reliability(session, region_id=region_id),
    )


@router.get("/regional-growth")
async def get_regional_growth_route(
    session: Annotated[AsyncSession, Depends(get_db)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
):
    """Returns month-over-month revenue growth per region."""

    return await _load_cached_analytics_payload(
        cache_service=cache_service,
        namespace="analytics.regional-growth",
        payload={},
        loader=lambda: get_regional_growth(session),
    )


@router.get("/forecast-runs")
async def get_forecast_runs(
    session: Annotated[AsyncSession, Depends(get_db)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
    run_date: Annotated[date | None, Query()] = None,
):
    """Returns the number of forecasts generated for a specific day."""

    try:
        async def loader():
            return {"count": await db_service.count_forecast_runs(session, run_date=run_date)}

        return await _load_cached_analytics_payload(
            cache_service=cache_service,
            namespace="analytics.forecast-runs",
            payload={"run_date": run_date},
            loader=loader,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
