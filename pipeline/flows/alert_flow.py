"""Alert refresh flow for SupplyIQ."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from prefect import flow
from redis import Redis
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.models.db_models import InventoryAlert


def refresh_alert_cache() -> dict[str, object]:
    """Refreshes the Redis alert cache from PostgreSQL."""

    database_url = os.getenv("PIPELINE_DATABASE_URL") or os.getenv("BACKEND_DATABASE_URL")
    redis_url = os.getenv("PIPELINE_REDIS_URL") or os.getenv("BACKEND_REDIS_URL")
    if not database_url or not redis_url:
        raise RuntimeError("PIPELINE_DATABASE_URL and PIPELINE_REDIS_URL must be set for alert flow execution.")

    engine = create_engine(database_url, pool_pre_ping=True)
    redis_client = Redis.from_url(redis_url, decode_responses=True)

    with Session(engine) as session:
        alerts = session.execute(select(InventoryAlert).where(InventoryAlert.acknowledged.is_(False))).scalars().all()

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "open_alert_count": len(alerts),
        "critical_alert_count": len([alert for alert in alerts if alert.severity == "critical"]),
    }
    redis_client.setex("supplyiq:pipeline:alert_summary", 300, str(payload))
    return payload


@flow(name="supplyiq-alert-flow")
def run_alert_flow() -> dict[str, object]:
    """Runs the Prefect alert refresh flow."""

    return refresh_alert_cache()


def run_alert_cli() -> dict[str, object]:
    """Runs alert refresh without starting the Prefect orchestration engine."""

    return refresh_alert_cache()


if __name__ == "__main__":
    run_alert_cli()
