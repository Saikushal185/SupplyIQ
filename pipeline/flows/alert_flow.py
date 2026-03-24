"""Alert refresh flow for SupplyIQ."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

try:
    from prefect import flow
except ModuleNotFoundError:  # pragma: no cover - lightweight fallback for local unit imports
    def flow(*_args, **_kwargs):
        def decorator(func):
            func.fn = func
            return func
        return decorator

try:
    import psycopg
except ModuleNotFoundError:  # pragma: no cover - dependency exists in the runtime image
    psycopg = None  # type: ignore[assignment]

try:
    from redis import Redis
except ModuleNotFoundError:  # pragma: no cover - dependency exists in the runtime image
    Redis = None  # type: ignore[assignment]

from pipeline.tasks.database import build_postgres_dsn


def refresh_alert_cache() -> dict[str, object]:
    """Refreshes the Redis alert cache from PostgreSQL."""

    if psycopg is None or Redis is None:  # pragma: no cover - exercised only when dependencies are absent
        raise RuntimeError("psycopg and redis must be installed to run alert refresh.")

    database_url = os.getenv("PIPELINE_DATABASE_URL") or os.getenv("BACKEND_DATABASE_URL")
    redis_url = os.getenv("PIPELINE_REDIS_URL") or os.getenv("BACKEND_REDIS_URL")
    if not database_url or not redis_url:
        raise RuntimeError("PIPELINE_DATABASE_URL and PIPELINE_REDIS_URL must be set for alert flow execution.")

    redis_client = Redis.from_url(redis_url, decode_responses=True)
    with psycopg.connect(build_postgres_dsn(database_url)) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH ranked_snapshots AS (
                    SELECT
                        inventory_snapshots.id,
                        inventory_snapshots.product_id,
                        inventory_snapshots.region_id,
                        inventory_snapshots.quantity,
                        inventory_snapshots.snapshot_date,
                        ROW_NUMBER() OVER (
                            PARTITION BY inventory_snapshots.product_id, inventory_snapshots.region_id
                            ORDER BY inventory_snapshots.snapshot_date DESC, inventory_snapshots.id DESC
                        ) AS snapshot_rank
                    FROM inventory_snapshots
                )
                SELECT
                    COUNT(*) AS open_alert_count,
                    SUM(
                        CASE
                            WHEN ranked_snapshots.quantity < COALESCE(products.reorder_point, 0) * 0.5 THEN 1
                            ELSE 0
                        END
                    ) AS critical_alert_count
                FROM ranked_snapshots
                JOIN products ON products.id = ranked_snapshots.product_id
                WHERE ranked_snapshots.snapshot_rank = 1
                  AND ranked_snapshots.quantity < COALESCE(products.reorder_point, 0)
                """
            )
            open_alert_count, critical_alert_count = cursor.fetchone() or (0, 0)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "open_alert_count": int(open_alert_count or 0),
        "critical_alert_count": int(critical_alert_count or 0),
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
