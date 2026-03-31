"""Seeds two years of historical SupplyIQ training data."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
import logging
import random
from typing import Any

try:
    import psycopg
except ModuleNotFoundError:  # pragma: no cover - exercised only in lightweight local test environments
    psycopg = None  # type: ignore[assignment]

try:
    import numpy as np
except ModuleNotFoundError:  # pragma: no cover - exercised only in lightweight local test environments
    np = None  # type: ignore[assignment]

from pipeline.tasks.database import build_postgres_dsn
from pipeline.tasks.reference_data import DEFAULT_PRODUCTS, DEFAULT_REGIONS

logger = logging.getLogger(__name__)


def _resolve_database_url() -> str:
    """Returns the backend database connection string for seeding."""

    import os

    database_url = os.getenv("DATABASE_URL") or os.getenv("BACKEND_DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set before running the seed script.")
    return build_postgres_dsn(database_url)


def _seasonal_demand_delta(category: str, month: int) -> float:
    """Returns the category-specific seasonal adjustment used in historical data."""

    if category == "electronics":
        return {
            11: 22.0,
            12: 28.0,
            1: 9.0,
        }.get(month, 2.0 if month in {6, 7} else 5.0)
    if category == "food":
        return 6.0
    if category == "apparel":
        return 11.0 if month in {10, 11, 12, 1, 2} else 4.5
    if category == "household":
        return 10.0 if month in {3, 4, 5} else 5.0
    return 4.0


def build_seed_dataset(*, end_date: date, days: int = 730) -> dict[str, list[dict[str, object]]]:
    """Builds the full historical dataset used for model training."""

    if np is not None:
        rng: Any = np.random.default_rng(42)
        uniform = lambda minimum, maximum: float(rng.uniform(minimum, maximum))
        normal = lambda mean, std_dev: float(rng.normal(mean, std_dev))
    else:
        rng = random.Random(42)
        uniform = lambda minimum, maximum: rng.uniform(minimum, maximum)
        normal = lambda mean, std_dev: rng.gauss(mean, std_dev)
    start_date = end_date - timedelta(days=days - 1)
    products = [dict(product) for product in DEFAULT_PRODUCTS]
    regions = [dict(region) for region in DEFAULT_REGIONS]
    daily_sales: list[dict[str, object]] = []
    inventory_snapshots: list[dict[str, object]] = []

    inventory_levels: dict[tuple[str, str], int] = defaultdict(int)
    reorder_lookup = {str(product["sku"]): int(product["reorder_point"]) for product in products}
    base_demand_lookup = {str(product["sku"]): float(product["base_demand"]) for product in products}

    for product in products:
        for region in regions:
            inventory_levels[(str(product["sku"]), str(region["name"]))] = int(reorder_lookup[str(product["sku"])] * 2.2)

    current_date = start_date
    while current_date <= end_date:
        weekday_factor = 0.94 if current_date.weekday() >= 5 else 1.08
        month = current_date.month
        for product in products:
            base_demand = base_demand_lookup[str(product["sku"])]
            seasonal_delta = _seasonal_demand_delta(str(product["category"]), month)
            for region in regions:
                regional_temp = float(region["climate_temp"]) + ((month - 6) * 0.9)
                traffic_index = round(uniform(0.2, 0.9), 4)
                noise = normal(0, max(base_demand * 0.1, 1.0))
                units_sold = max(int(round((base_demand + seasonal_delta + noise) * weekday_factor)), 0)
                daily_sales.append(
                    {
                        "sku": product["sku"],
                        "region_name": region["name"],
                        "category": product["category"],
                        "sale_date": current_date,
                        "units_sold": units_sold,
                        "revenue": round(units_sold * float(product["unit_cost"]), 2),
                        "weather_temp": round(regional_temp, 2),
                        "traffic_index": traffic_index,
                    }
                )

                scope_key = (str(product["sku"]), str(region["name"]))
                opening_inventory = inventory_levels[scope_key]
                closing_inventory = max(opening_inventory - units_sold, 0)
                if closing_inventory < reorder_lookup[str(product["sku"])]:
                    closing_inventory += int(reorder_lookup[str(product["sku"])] * uniform(0.8, 1.6))
                inventory_levels[scope_key] = closing_inventory
                inventory_snapshots.append(
                    {
                        "sku": product["sku"],
                        "region_name": region["name"],
                        "snapshot_date": current_date,
                        "quantity": closing_inventory,
                    }
                )

        current_date += timedelta(days=1)

    return {
        "products": products,
        "regions": regions,
        "daily_sales": daily_sales,
        "inventory_snapshots": inventory_snapshots,
    }


def _upsert_reference_data(cursor: Any, dataset: dict[str, list[dict[str, object]]]) -> tuple[dict[str, object], dict[str, object]]:
    """Upserts products and regions and returns their database ids."""

    product_ids: dict[str, object] = {}
    region_ids: dict[str, object] = {}

    for product in dataset["products"]:
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
                product["sku"],
                product["name"],
                product["category"],
                product["unit_cost"],
                product["reorder_point"],
            ),
        )
        product_ids[str(product["sku"])] = cursor.fetchone()[0]

    for region in dataset["regions"]:
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
                region["name"],
                region["country"],
                region["timezone"],
            ),
        )
        region_ids[str(region["name"])] = cursor.fetchone()[0]

    return product_ids, region_ids


def seed_database(*, end_date: date | None = None, days: int = 730) -> dict[str, int]:
    """Seeds the database with the historical dataset used for model training."""

    if psycopg is None:  # pragma: no cover - exercised only when dependency is absent
        raise RuntimeError("psycopg must be installed to run the seed script.")

    resolved_end_date = end_date or datetime.now(UTC).date() - timedelta(days=1)
    dataset = build_seed_dataset(end_date=resolved_end_date, days=days)
    counts = {
        "products": len(dataset["products"]),
        "regions": len(dataset["regions"]),
        "daily_sales": len(dataset["daily_sales"]),
        "inventory_snapshots": len(dataset["inventory_snapshots"]),
    }

    with psycopg.connect(_resolve_database_url()) as connection:
        with connection.cursor() as cursor:
            product_ids, region_ids = _upsert_reference_data(cursor, dataset)

            cursor.executemany(
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
                [
                    (
                        product_ids[str(row["sku"])],
                        region_ids[str(row["region_name"])],
                        row["sale_date"],
                        row["units_sold"],
                        row["revenue"],
                        row["weather_temp"],
                        row["traffic_index"],
                    )
                    for row in dataset["daily_sales"]
                ],
            )

            cursor.executemany(
                """
                INSERT INTO inventory_snapshots (product_id, region_id, quantity, snapshot_date)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (product_id, region_id, snapshot_date)
                DO UPDATE SET quantity = EXCLUDED.quantity
                """,
                [
                    (
                        product_ids[str(row["sku"])],
                        region_ids[str(row["region_name"])],
                        row["quantity"],
                        row["snapshot_date"],
                    )
                    for row in dataset["inventory_snapshots"]
                ],
            )
        connection.commit()

    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    result = seed_database()
    logger.info("Seeded %s products, %s regions, %s daily_sales rows, and %s inventory_snapshots rows.", result["products"], result["regions"], result["daily_sales"], result["inventory_snapshots"])
