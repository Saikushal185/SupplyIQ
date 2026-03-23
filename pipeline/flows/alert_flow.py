"""Alert refresh flow for SupplyIQ."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from prefect import flow
import psycopg
from redis import Redis
from pipeline.tasks.database import build_postgres_dsn


def refresh_alert_cache() -> dict[str, object]:
    """Refreshes the Redis alert cache from PostgreSQL."""

    database_url = os.getenv("PIPELINE_DATABASE_URL") or os.getenv("BACKEND_DATABASE_URL")
    redis_url = os.getenv("PIPELINE_REDIS_URL") or os.getenv("BACKEND_REDIS_URL")
    if not database_url or not redis_url:
        raise RuntimeError("PIPELINE_DATABASE_URL and PIPELINE_REDIS_URL must be set for alert flow execution.")

    redis_client = Redis.from_url(redis_url, decode_responses=True)
    with psycopg.connect(build_postgres_dsn(database_url)) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT severity
                FROM inventory_alerts
                WHERE acknowledged = FALSE
                """
            )
            severities = [row[0] for row in cursor.fetchall()]

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "open_alert_count": len(severities),
        "critical_alert_count": len([severity for severity in severities if severity == "critical"]),
    }
    redis_client.setex("supplyiq:pipeline:alert_summary", 300, json.dumps(payload))
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
