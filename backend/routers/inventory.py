"""Inventory routes for SupplyIQ."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_db
from backend.services import db_service
from backend.services.response_service import build_response

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/summary")
async def get_inventory_summary(
    session: Annotated[AsyncSession, Depends(get_db)],
    region_id: Annotated[UUID | None, Query()] = None,
):
    """Returns current stock levels across tracked products and regions."""

    data = await db_service.get_inventory_summary(session, region_id=region_id)
    return build_response(data)


@router.get("/low-stock")
async def get_low_stock(
    session: Annotated[AsyncSession, Depends(get_db)],
    region_id: Annotated[UUID | None, Query()] = None,
):
    """Returns positions that are currently below their reorder point."""

    data = await db_service.get_low_stock(session, region_id=region_id)
    return build_response(data)


@router.get("/{product_id}/history")
async def get_inventory_history(
    product_id: Annotated[UUID, Path()],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """Returns the last 90 days of inventory snapshots for a product."""

    data = await db_service.get_inventory_history(session, product_id=product_id, days=90)
    return build_response(data)
