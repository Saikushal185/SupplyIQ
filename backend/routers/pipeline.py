"""Pipeline status routes for SupplyIQ."""

from __future__ import annotations

import httpx
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.dependencies import AuthContext, require_roles
from backend.services.pipeline_service import get_latest_pipeline_status
from backend.services.response_service import build_response

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

admin_only = require_roles("admin")


@router.get("/status")
async def get_pipeline_status(
    _: Annotated[AuthContext, Depends(admin_only)],
):
    """Returns the latest Prefect flow run status for administrators."""

    try:
        data = await get_latest_pipeline_status()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Unable to load Prefect pipeline status right now.") from exc
    return build_response(data)
