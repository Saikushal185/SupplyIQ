"""Local ingestion pipeline status visibility."""

from __future__ import annotations

from datetime import datetime

from backend.services.cache_service import CacheService

LAST_RUN_KEY = "supplyiq:pipeline:last_run"
FLOW_NAME = "supplyiq-ingestion-flow"


def _empty_pipeline_status(*, state_name: str) -> dict[str, object]:
    """Returns a consistent placeholder payload when no run has been recorded."""

    return {
        "flow_run_id": None,
        "flow_name": FLOW_NAME,
        "deployment_id": None,
        "deployment_name": None,
        "state_type": "UNKNOWN",
        "state_name": state_name,
        "start_time": None,
        "end_time": None,
        "next_scheduled_run_time": None,
    }


async def get_latest_pipeline_status() -> dict[str, object]:
    """Returns the latest ingestion run recorded in Redis by the pipeline."""

    cache_service = CacheService()
    try:
        raw = await cache_service.get_json(LAST_RUN_KEY)
    finally:
        await cache_service.close()

    if not isinstance(raw, dict):
        return _empty_pipeline_status(state_name="No runs yet")

    return {
        "flow_run_id": raw.get("run_id"),
        "flow_name": FLOW_NAME,
        "deployment_id": None,
        "deployment_name": None,
        "state_type": "COMPLETED",
        "state_name": "Completed",
        "start_time": _parse_datetime(raw.get("started_at")),
        "end_time": _parse_datetime(raw.get("completed_at")),
        "next_scheduled_run_time": None,
    }


def _parse_datetime(value: object) -> datetime | None:
    """Parses ISO datetime strings into Python datetime objects."""

    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return None
