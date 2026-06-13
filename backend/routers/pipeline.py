"""Pipeline status routes for SupplyIQ."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.services.pipeline_service import get_latest_pipeline_status
from backend.services.response_service import build_response

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.get("/status")
async def get_pipeline_status():
    """Returns the latest ingestion pipeline run status."""

    try:
        data = await get_latest_pipeline_status()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return build_response(data)
