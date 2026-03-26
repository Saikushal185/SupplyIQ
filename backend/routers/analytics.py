"""Analytics routes for SupplyIQ."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_cache_service, get_db
from backend.services import analytics_service, db_service
from backend.services.cache_service import CacheService
from backend.services.response_service import build_response

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _normalize_date_range(
    start_date: date | None,
    end_date: date | None,
) -> tuple[date | None, date | None]:
    """Rejects inverted date filters before running SQL work."""

    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be on or before end_date.")
    return start_date, end_date


async def _load_cached_analytics_payload(
    *,
    cache_service: CacheService,
    cache_namespace: str,
    cache_payload: dict[str, object],
    loader,
) -> tuple[object, bool]:
    """Loads analytics data from Redis or computes and stores it."""

    cache_key = cache_service.build_key(cache_namespace, cache_payload)
    cached_value = await cache_service.get_json(cache_key)
    if cached_value is not None:
        return cached_value, True

    data = await loader()
    await cache_service.set_json(cache_key, data)
    return data, False


@router.get("/sales")
async def get_sales_analytics(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    region_id: Annotated[UUID | None, Query()] = None,
):
    """Returns daily sales aggregated by region, filtered by date range when provided."""

    start_date, end_date = _normalize_date_range(start_date, end_date)
    data, cached = await _load_cached_analytics_payload(
        cache_service=cache_service,
        cache_namespace=request.url.path,
        cache_payload={
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
    return build_response(data, cached=cached)


@router.get("/filter-options")
async def get_filter_options(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
):
    """Returns region and category metadata used by the analytics filter bar."""

    data, cached = await _load_cached_analytics_payload(
        cache_service=cache_service,
        cache_namespace=request.url.path,
        cache_payload={},
        loader=lambda: analytics_service.get_analytics_filter_options(session),
    )
    return build_response(data, cached=cached)


@router.get("/turnover")
async def get_inventory_turnover(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
):
    """Returns inventory turnover ratio per product."""

    start_date, end_date = _normalize_date_range(start_date, end_date)
    data, cached = await _load_cached_analytics_payload(
        cache_service=cache_service,
        cache_namespace=request.url.path,
        cache_payload={
            "start_date": start_date,
            "end_date": end_date,
        },
        loader=lambda: db_service.get_inventory_turnover(
            session,
            start_date=start_date,
            end_date=end_date,
        ),
    )
    return build_response(data, cached=cached)


@router.get("/supplier-reliability")
async def get_supplier_reliability(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
):
    """Returns on-time delivery reliability by supplier."""

    data, cached = await _load_cached_analytics_payload(
        cache_service=cache_service,
        cache_namespace=request.url.path,
        cache_payload={},
        loader=lambda: db_service.get_supplier_reliability(session),
    )
    return build_response(data, cached=cached)


@router.get("/regional-growth")
async def get_regional_growth(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
):
    """Returns the latest month-over-month revenue growth by region."""

    data, cached = await _load_cached_analytics_payload(
        cache_service=cache_service,
        cache_namespace=request.url.path,
        cache_payload={},
        loader=lambda: analytics_service.get_regional_growth(session),
    )
    return build_response(data, cached=cached)
