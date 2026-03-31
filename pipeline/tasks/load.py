"""Load tasks for SupplyIQ pipeline."""

from __future__ import annotations

import os
from typing import Any

try:
    import psycopg
except ModuleNotFoundError:  # pragma: no cover - dependency exists in the runtime image
    psycopg = None  # type: ignore[assignment]

try:
    from redis import Redis
except ModuleNotFoundError:  # pragma: no cover - dependency exists in the runtime image
    Redis = None  # type: ignore[assignment]

try:
    from prefect import task
except ModuleNotFoundError:  # pragma: no cover - lightweight fallback for local unit imports
    def task(*_args, **_kwargs):
        def decorator(func):
            func.fn = func
            return func
        return decorator

from pipeline.tasks.database import build_postgres_dsn, get_pipeline_database_url


def build_inventory_rows_for_load(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Builds the final inventory upsert rows from opening quantity and same-day demand."""

    return [
        {
            **row,
            "quantity": max(int(row.get("opening_quantity") or 0) - int(row.get("units_sold") or 0), 0),
        }
        for row in rows
    ]


def invalidate_analytics_cache(redis_client: Any) -> int:
    """Invalidates analytics cache keys after a successful load."""

    deleted = 0
    for pattern in ("analytics:*", "supplyiq:analytics:*"):
        keys = list(redis_client.scan_iter(match=pattern))
        if keys:
            deleted += int(redis_client.delete(*keys))
    return deleted


def _get_redis_url() -> str | None:
    """Returns the configured Redis URL for cache invalidation."""

    return os.getenv("PIPELINE_REDIS_URL") or os.getenv("BACKEND_REDIS_URL") or os.getenv("REDIS_URL")


def _upsert_region(cursor: Any, payload: dict[str, object]) -> object:
    """Upserts a region row and returns its primary key."""

    cursor.execute(
        """
        INSERT INTO regions (name, country, timezone)
        VALUES (%s, %s, %s)
        ON CONFLICT (name)
        DO UPDATE SET
            country = EXCLUDED.country,
            timezone = EXCLUDED.timezone
        RETURNING id
        """,
        (
            payload["name"],
            payload.get("country"),
            payload.get("timezone"),
        ),
    )
    created = cursor.fetchone()
    if created is None:
        raise RuntimeError("Region upsert did not return an id.")
    return created[0]


def _upsert_product(cursor: Any, payload: dict[str, object]) -> object:
    """Upserts a product row and returns its primary key."""

    cursor.execute(
        """
        INSERT INTO products (sku, name, category, unit_cost, reorder_point)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (sku)
        DO UPDATE SET
            name = EXCLUDED.name,
            category = EXCLUDED.category,
            unit_cost = EXCLUDED.unit_cost,
            reorder_point = EXCLUDED.reorder_point
        RETURNING id
        """,
        (
            payload["sku"],
            payload["name"],
            payload.get("category"),
            payload.get("unit_cost"),
            payload.get("reorder_point"),
        ),
    )
    created = cursor.fetchone()
    if created is None:
        raise RuntimeError("Product upsert did not return an id.")
    return created[0]


def _upsert_daily_sale(cursor: Any, payload: dict[str, object]) -> None:
    """Upserts a daily sales row using PostgreSQL ON CONFLICT semantics."""

    cursor.execute(
        """
        INSERT INTO daily_sales (product_id, region_id, sale_date, units_sold, revenue, weather_temp, traffic_index)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (product_id, region_id, sale_date)
        DO UPDATE SET
            units_sold = EXCLUDED.units_sold,
            revenue = EXCLUDED.revenue,
            weather_temp = EXCLUDED.weather_temp,
            traffic_index = EXCLUDED.traffic_index
        """,
        (
            payload["product_id"],
            payload["region_id"],
            payload["sale_date"],
            payload["units_sold"],
            payload["revenue"],
            payload.get("weather_temp"),
            payload.get("traffic_index"),
        ),
    )


def _upsert_inventory_snapshot(cursor: Any, payload: dict[str, object]) -> None:
    """Upserts the current-day inventory quantity after subtracting same-day demand."""

    cursor.execute(
        """
        INSERT INTO inventory_snapshots (product_id, region_id, quantity, snapshot_date)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (product_id, region_id, snapshot_date)
        DO UPDATE SET quantity = EXCLUDED.quantity
        """,
        (
            payload["product_id"],
            payload["region_id"],
            payload["quantity"],
            payload["snapshot_date"],
        ),
    )


@task(name="load_supply_data")
def load_supply_data(transformed_data: dict[str, list[dict[str, object]]]) -> dict[str, int]:
    """Loads validated supply data into PostgreSQL and clears analytics caches."""

    if psycopg is None:  # pragma: no cover - exercised only when dependency is absent
        raise RuntimeError("psycopg must be installed to run pipeline database loads.")

    counts = {
        "regions": 0,
        "products": 0,
        "daily_sales": 0,
        "inventory_snapshots": 0,
        "rejected_daily_sales": len(transformed_data.get("rejected_daily_sales", [])),
        "invalidated_cache_keys": 0,
    }
    region_ids: dict[str, object] = {}
    product_ids: dict[str, object] = {}
    database_dsn = build_postgres_dsn(get_pipeline_database_url())

    with psycopg.connect(database_dsn) as connection:
        with connection.cursor() as cursor:
            for payload in transformed_data.get("regions", []):
                region_id = payload.get("region_id")
                if region_id is not None:
                    region_ids[str(region_id)] = region_id
                region_ids[str(payload["name"])] = _upsert_region(cursor, payload)
                counts["regions"] += 1

            for payload in transformed_data.get("products", []):
                product_id = payload.get("product_id")
                if product_id is not None:
                    product_ids[str(product_id)] = product_id
                product_ids[str(payload["sku"])] = _upsert_product(cursor, payload)
                counts["products"] += 1

            for payload in transformed_data.get("daily_sales", []):
                _upsert_daily_sale(
                    cursor,
                    {
                        "product_id": product_ids.get(str(payload["product_id"]), payload["product_id"]),
                        "region_id": region_ids.get(str(payload["region_id"]), payload["region_id"]),
                        "sale_date": payload["sale_date"],
                        "units_sold": int(payload["units_sold"]),
                        "revenue": payload["revenue"],
                        "weather_temp": payload.get("weather_temp"),
                        "traffic_index": payload.get("traffic_index"),
                    },
                )
                counts["daily_sales"] += 1

            for payload in build_inventory_rows_for_load(transformed_data.get("inventory_snapshots", [])):
                _upsert_inventory_snapshot(
                    cursor,
                    {
                        "product_id": product_ids.get(str(payload["product_id"]), payload["product_id"]),
                        "region_id": region_ids.get(str(payload["region_id"]), payload["region_id"]),
                        "snapshot_date": payload["snapshot_date"],
                        "quantity": payload["quantity"],
                    },
                )
                counts["inventory_snapshots"] += 1

        connection.commit()

    redis_url = _get_redis_url()
    if Redis is not None and redis_url:
        redis_client = Redis.from_url(redis_url, decode_responses=True)
        try:
            counts["invalidated_cache_keys"] = invalidate_analytics_cache(redis_client)
        finally:
            redis_client.close()

    return counts
