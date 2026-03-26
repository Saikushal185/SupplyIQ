"""Prefect Cloud integration helpers for pipeline status visibility."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from backend.settings import get_settings


def _empty_pipeline_status(*, flow_name: str | None, state_name: str) -> dict[str, object]:
    """Returns a consistent placeholder payload when Prefect data is unavailable."""

    return {
        "flow_run_id": None,
        "flow_name": flow_name,
        "deployment_id": None,
        "deployment_name": None,
        "state_type": "UNKNOWN",
        "state_name": state_name,
        "start_time": None,
        "end_time": None,
        "next_scheduled_run_time": None,
    }


async def get_latest_pipeline_status() -> dict[str, object]:
    """Returns the latest Prefect flow run status using the configured Cloud API."""

    settings = get_settings()
    if not settings.prefect_api_url or not settings.prefect_api_key:
        return _empty_pipeline_status(flow_name=settings.prefect_flow_name, state_name="Not configured")

    latest_run_payload: dict[str, object] = {
        "sort": "ID_DESC",
        "limit": 1,
    }
    if settings.prefect_flow_name:
        latest_run_payload["flows"] = {
            "name": {
                "any_": [settings.prefect_flow_name],
            }
        }

    headers = {
        "Authorization": f"Bearer {settings.prefect_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{settings.prefect_api_url.rstrip('/')}/flow_runs/filter",
            json=latest_run_payload,
            headers=headers,
        )
        response.raise_for_status()
        rows = response.json()

    if not rows:
        return _empty_pipeline_status(flow_name=settings.prefect_flow_name, state_name="No flow runs found")

    latest_run = rows[0]
    state = latest_run.get("state") if isinstance(latest_run.get("state"), dict) else {}
    next_scheduled_run_time = await _load_next_scheduled_run_time(
        prefect_api_url=settings.prefect_api_url,
        prefect_api_key=settings.prefect_api_key,
        prefect_flow_name=settings.prefect_flow_name,
    )

    return {
        "flow_run_id": str(latest_run.get("id")) if latest_run.get("id") is not None else None,
        "flow_name": latest_run.get("name"),
        "deployment_id": str(latest_run.get("deployment_id")) if latest_run.get("deployment_id") is not None else None,
        "deployment_name": latest_run.get("deployment_name"),
        "state_type": state.get("type") or latest_run.get("state_type"),
        "state_name": state.get("name") or latest_run.get("state_name"),
        "start_time": _parse_datetime(latest_run.get("start_time")),
        "end_time": _parse_datetime(latest_run.get("end_time")),
        "next_scheduled_run_time": next_scheduled_run_time,
    }


async def _load_next_scheduled_run_time(
    *,
    prefect_api_url: str,
    prefect_api_key: str,
    prefect_flow_name: str | None,
) -> datetime | None:
    """Best-effort lookup for the next scheduled Prefect flow run."""

    payload: dict[str, object] = {
        "sort": "EXPECTED_START_TIME_ASC",
        "limit": 1,
        "flow_runs": {
            "state": {
                "type": {
                    "any_": ["SCHEDULED"],
                }
            },
            "start_time": {
                "after_": datetime.now(timezone.utc).isoformat(),
            },
        },
    }
    if prefect_flow_name:
        payload["flows"] = {
            "name": {
                "any_": [prefect_flow_name],
            }
        }

    headers = {
        "Authorization": f"Bearer {prefect_api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{prefect_api_url.rstrip('/')}/flow_runs/filter",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            rows = response.json()
    except httpx.HTTPError:
        return None

    if not rows:
        return None

    next_run = rows[0]
    return _parse_datetime(next_run.get("expected_start_time") or next_run.get("start_time"))


def _parse_datetime(value: object) -> datetime | None:
    """Parses Prefect datetime strings into Python datetime objects."""

    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    return None
