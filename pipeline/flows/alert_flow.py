"""Inventory alert flow for SupplyIQ."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

try:
    from prefect import flow
except ModuleNotFoundError:  # pragma: no cover - lightweight fallback for local unit imports
    def flow(*_args, **_kwargs):
        def decorator(func):
            func.fn = func
            return func
        return decorator

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover - dependency exists in the runtime image
    httpx = None  # type: ignore[assignment]

try:
    import psycopg
except ModuleNotFoundError:  # pragma: no cover - dependency exists in the runtime image
    psycopg = None  # type: ignore[assignment]

try:
    from redis import Redis
except ModuleNotFoundError:  # pragma: no cover - dependency exists in the runtime image
    Redis = None  # type: ignore[assignment]

from pipeline.tasks.database import build_postgres_dsn

logger = logging.getLogger(__name__)
ALERT_TTL_SECONDS = 60 * 60 * 24


def _get_database_url() -> str:
    """Returns the database URL used by the alert flow."""

    database_url = os.getenv("PIPELINE_DATABASE_URL") or os.getenv("BACKEND_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set for alert flow execution.")
    return database_url


def _get_redis_url() -> str:
    """Returns the Redis URL used by the alert flow."""

    redis_url = os.getenv("PIPELINE_REDIS_URL") or os.getenv("BACKEND_REDIS_URL") or os.getenv("REDIS_URL")
    if not redis_url:
        raise RuntimeError("REDIS_URL must be set for alert flow execution.")
    return redis_url


def should_send_inventory_alert(redis_client: Any, *, product_id: Any, now: datetime | None = None) -> bool:
    """Rate-limits inventory alerts to one email per product per 24 hours."""

    timestamp = (now or datetime.now(UTC)).astimezone(UTC)
    cache_key = f"inventory-alert:{product_id}"
    if redis_client.get(cache_key):
        return False
    redis_client.setex(cache_key, ALERT_TTL_SECONDS, timestamp.isoformat())
    return True


def query_low_inventory_rows(connection: Any) -> list[dict[str, object]]:
    """Returns the latest product-region positions below reorder point."""

    with connection.cursor() as cursor:
        cursor.execute(
            """
            WITH ranked_snapshots AS (
                SELECT
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
                products.id,
                products.name,
                products.reorder_point,
                regions.name,
                ranked_snapshots.quantity,
                ranked_snapshots.snapshot_date
            FROM ranked_snapshots
            JOIN products ON products.id = ranked_snapshots.product_id
            JOIN regions ON regions.id = ranked_snapshots.region_id
            WHERE ranked_snapshots.snapshot_rank = 1
              AND ranked_snapshots.quantity < COALESCE(products.reorder_point, 0)
            ORDER BY ranked_snapshots.quantity ASC, products.name ASC
            """
        )
        rows = cursor.fetchall()

    return [
        {
            "product_id": product_id,
            "product_name": product_name,
            "reorder_point": int(reorder_point or 0),
            "region_name": region_name,
            "quantity": int(quantity or 0),
            "snapshot_date": snapshot_date,
        }
        for product_id, product_name, reorder_point, region_name, quantity, snapshot_date in rows
    ]


async def send_inventory_alert_email(
    *,
    recipient_email: str,
    product_name: str,
    region_name: str,
    quantity: int,
    reorder_point: int,
) -> bool:
    """Sends a low-inventory email through Resend."""

    if httpx is None:  # pragma: no cover - exercised only when dependency is absent
        raise RuntimeError("httpx must be installed to send inventory alert emails.")

    resend_api_key = os.getenv("RESEND_API_KEY") or os.getenv("BACKEND_RESEND_API_KEY")
    alert_from = os.getenv("ALERT_EMAIL_FROM") or os.getenv("RESEND_FROM_EMAIL")
    if not resend_api_key or not alert_from or not recipient_email:
        logger.warning("Skipping inventory alert email because Resend is not fully configured.")
        return False

    payload = {
        "from": alert_from,
        "to": [recipient_email],
        "subject": f"SupplyIQ inventory alert: {product_name}",
        "text": (
            f"{product_name} in {region_name} is below its reorder point.\n"
            f"Current quantity: {quantity}\n"
            f"Reorder point: {reorder_point}"
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


async def dispatch_inventory_alerts(
    rows: list[dict[str, object]],
    *,
    redis_client: Any,
    recipient_email: str | None,
    email_sender: Any | None = None,
    now: datetime | None = None,
) -> dict[str, int]:
    """Dispatches inventory emails while honoring the per-product rate limit."""

    email_sender = email_sender or send_inventory_alert_email
    stats = {
        "queried": len(rows),
        "sent": 0,
        "rate_limited": 0,
        "skipped": 0,
        "failed": 0,
    }
    if not recipient_email:
        stats["skipped"] = len(rows)
        return stats

    for row in rows:
        if not should_send_inventory_alert(redis_client, product_id=row["product_id"], now=now):
            stats["rate_limited"] += 1
            continue
        try:
            email_sent = await email_sender(
                recipient_email=recipient_email,
                product_name=str(row["product_name"]),
                region_name=str(row["region_name"]),
                quantity=int(row["quantity"]),
                reorder_point=int(row["reorder_point"]),
            )
        except Exception:  # pragma: no cover - exercised only by live integrations
            logger.exception("Unable to send inventory alert for product %s", row["product_id"])
            stats["failed"] += 1
            continue

        if email_sent:
            stats["sent"] += 1
        else:
            stats["skipped"] += 1

    return stats


def refresh_alert_cache(redis_client: Any, rows: list[dict[str, object]], *, generated_at: datetime) -> dict[str, object]:
    """Refreshes the alert summary cache after evaluating low-stock positions."""

    payload = {
        "generated_at": generated_at.isoformat(),
        "open_alert_count": len(rows),
        "critical_alert_count": sum(1 for row in rows if int(row["quantity"]) < max(int(row["reorder_point"]) // 2, 1)),
    }
    redis_client.setex("supplyiq:pipeline:alert_summary", 300, json.dumps(payload))
    return payload


def run_inventory_alerts() -> dict[str, object]:
    """Queries low-stock inventory and sends rate-limited alert emails."""

    if psycopg is None or Redis is None:  # pragma: no cover - exercised only when dependencies are absent
        raise RuntimeError("psycopg and redis must be installed to run alert refresh.")

    generated_at = datetime.now(UTC)
    database_url = build_postgres_dsn(_get_database_url())
    redis_client = Redis.from_url(_get_redis_url(), decode_responses=True)

    with psycopg.connect(database_url) as connection:
        rows = query_low_inventory_rows(connection)

    dispatch_stats = asyncio.run(
        dispatch_inventory_alerts(
            rows,
            redis_client=redis_client,
            recipient_email=os.getenv("ALERT_EMAIL_TO") or os.getenv("ALERT_EMAIL_FROM"),
            now=generated_at,
        )
    )
    cache_payload = refresh_alert_cache(redis_client, rows, generated_at=generated_at)
    redis_client.close()
    return {
        **dispatch_stats,
        **cache_payload,
    }


@flow(name="supplyiq-alert-flow")
def run_alert_flow() -> dict[str, object]:
    """Runs the Prefect low-stock alert flow."""

    return run_inventory_alerts()


def run_alert_cli() -> dict[str, object]:
    """Runs the alert flow without starting the Prefect orchestration engine."""

    return run_inventory_alerts()


if __name__ == "__main__":
    run_alert_cli()
