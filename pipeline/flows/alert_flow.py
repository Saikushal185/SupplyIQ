"""Alert refresh flow for SupplyIQ."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
import logging

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

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover - dependency exists in the runtime image
    httpx = None  # type: ignore[assignment]

from pipeline.tasks.database import build_postgres_dsn

logger = logging.getLogger(__name__)


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


async def send_stockout_risk_email(
    *,
    recipient_email: str,
    product_name: str,
    region_name: str,
    stockout_date: str,
    current_stock_level: int,
) -> bool:
    """Sends a stockout alert email through Resend for forecast-triggered risks."""

    if httpx is None:  # pragma: no cover - exercised only when dependency is absent
        raise RuntimeError("httpx must be installed to send stockout alert emails.")

    resend_api_key = os.getenv("BACKEND_RESEND_API_KEY") or os.getenv("RESEND_API_KEY")
    resend_from_email = os.getenv("BACKEND_RESEND_FROM_EMAIL") or os.getenv("RESEND_FROM_EMAIL")
    if not resend_api_key or not resend_from_email or not recipient_email:
        logger.warning("Skipping stockout alert email because Resend is not fully configured.")
        return False

    payload = {
        "from": resend_from_email,
        "to": [recipient_email],
        "subject": f"⚠️ SupplyIQ Stockout Risk: {product_name} in {region_name}",
        "text": (
            f"SupplyIQ detected a stockout risk for {product_name} in {region_name}.\n"
            f"Predicted stockout date: {stockout_date}\n"
            f"Current stock level: {current_stock_level} units"
        ),
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {resend_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
    return True


if __name__ == "__main__":
    run_alert_cli()
