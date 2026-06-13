"""Helpers for building consistent API response envelopes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def build_error_response(detail: str, *, status_code: int = 400) -> JSONResponse:
    """Wraps error details in the shared API response contract."""

    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(
            {
                "error": detail,
                "meta": {
                    "timestamp": datetime.now(timezone.utc),
                    "cached": False,
                },
            }
        ),
    )


def build_response(data: object, *, cached: bool = False, status_code: int = 200) -> JSONResponse:
    """Wraps payloads in the shared `{data, meta}` API response contract."""

    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(
            {
                "data": data,
                "meta": {
                    "timestamp": datetime.now(timezone.utc),
                    "cached": cached,
                },
            }
        ),
    )
