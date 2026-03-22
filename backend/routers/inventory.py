"""Inventory routes for SupplyIQ."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.dependencies import get_cache_service, get_db
from backend.models.schemas import InventoryPositionResponse, InventoryQuery, InventoryRebalanceRequest, InventoryRebalanceResponse
from backend.services import db_service
from backend.services.cache_service import CacheService

router = APIRouter(prefix="/inventory", tags=["inventory"])


def build_inventory_query(
    region_code: Annotated[str | None, Query(min_length=2, max_length=32)] = None,
    below_reorder_only: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> InventoryQuery:
    """Builds the validated inventory query model."""

    return InventoryQuery(region_code=region_code, below_reorder_only=below_reorder_only, limit=limit)


@router.get("/positions", response_model=InventoryPositionResponse)
def get_inventory_positions(
    query: Annotated[InventoryQuery, Depends(build_inventory_query)],
    session: Annotated[Session, Depends(get_db)],
    cache_service: Annotated[CacheService, Depends(get_cache_service)],
) -> InventoryPositionResponse:
    """Returns current inventory positions."""

    cache_key = cache_service.build_key("inventory_positions", query.model_dump())
    cached = cache_service.get_json(cache_key)
    if cached is not None:
        return InventoryPositionResponse.model_validate(cached)

    response = InventoryPositionResponse(
        generated_at=datetime.now(timezone.utc),
        items=db_service.list_inventory_positions(
            session,
            region_code=query.region_code,
            below_reorder_only=query.below_reorder_only,
            limit=query.limit,
        ),
    )
    cache_service.set_json(cache_key, response.model_dump())
    return response


@router.get("/stockouts", response_model=InventoryPositionResponse)
def get_stockout_candidates(
    query: Annotated[InventoryQuery, Depends(build_inventory_query)],
    session: Annotated[Session, Depends(get_db)],
) -> InventoryPositionResponse:
    """Returns inventory positions already below their reorder threshold."""

    return InventoryPositionResponse(
        generated_at=datetime.now(timezone.utc),
        items=db_service.list_inventory_positions(
            session,
            region_code=query.region_code,
            below_reorder_only=True,
            limit=query.limit,
        ),
    )


@router.post("/rebalance", response_model=InventoryRebalanceResponse)
def rebalance_inventory(
    payload: InventoryRebalanceRequest,
    session: Annotated[Session, Depends(get_db)],
) -> InventoryRebalanceResponse:
    """Moves inventory from one region to another by recording new snapshots."""

    try:
        return db_service.rebalance_inventory(session, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
